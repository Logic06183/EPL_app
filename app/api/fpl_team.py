"""
FPL Team Import API
Fetch a user's live FPL team by team ID, suggest optimal transfers, and
build a personalised briefing card for the user's squad.
"""

import asyncio
import logging
import os
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
from ..services.optimizer import (
    candidates_from_elements, chip_advice, chips_available, estimate_free_transfers, optimise,
)
from ..services.league import league_view
from ..services.prediction_service import PredictionService, get_prediction_service
from ..services import gemini_service
from ..utils.cache import get_cache_manager
from ..auth.firebase_auth import (
    get_current_user, get_effective_plan, get_db,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{team_id}")
async def get_fpl_team(
    team_id:      int,
    data_service: FPLDataService = Depends(get_data_service),
    user:         dict           = Depends(get_current_user),
):
    """
    Fetch an FPL manager's team for the current gameweek.
    team_id is the numeric ID visible in your FPL URL:
      https://fantasy.premierleague.com/entry/{team_id}/history
    """
    # Open to all users during launch — flip require_pro(user) back on later.
    try:
        gw_info = await data_service.get_gameweek_info()
        cur = gw_info.get("current") or gw_info.get("next") or {}
        gw_id = cur.get("id", 1)

        client = await data_service._get_client()

        # Team profile
        team_resp = await client.get(
            f"https://fantasy.premierleague.com/api/entry/{team_id}/"
        )
        if team_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="FPL team not found. Check the team ID.")
        team_resp.raise_for_status()
        team_meta = team_resp.json()

        # GW picks
        picks_resp = await client.get(
            f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{gw_id}/picks/"
        )
        picks_resp.raise_for_status()
        picks_data = picks_resp.json()

        bootstrap = await data_service.get_bootstrap_data()
        elements  = {p["id"]: p for p in bootstrap.get("elements", [])}
        teams_map = {t["id"]: t for t in bootstrap.get("teams", [])}
        pos_map   = {p["id"]: p for p in bootstrap.get("element_types", [])}

        enriched = []
        for pick in picks_data.get("picks", []):
            p   = elements.get(pick["element"], {})
            tm  = teams_map.get(p.get("team", 0), {})
            pos = pos_map.get(p.get("element_type", 0), {})
            enriched.append({
                "id":               pick["element"],
                "name":             p.get("web_name", ""),
                "full_name":        f"{p.get('first_name','')} {p.get('second_name','')}".strip(),
                "team_name":        tm.get("name", ""),
                "position_name":    pos.get("singular_name_short", ""),
                "position":         p.get("element_type", 0),
                "price":            float(p.get("now_cost", 0)) / 10,
                "form":             float(p.get("form", 0)),
                "total_points":     int(p.get("total_points", 0)),
                "ownership":        float(p.get("selected_by_percent", 0)),
                "news":             p.get("news", ""),
                "chance_of_playing": p.get("chance_of_playing_next_round"),
                "is_captain":       pick.get("is_captain", False),
                "is_vice_captain":  pick.get("is_vice_captain", False),
                "multiplier":       pick.get("multiplier", 1),
                "is_starting":      pick.get("position", 0) <= 11,
                "squad_position":   pick.get("position", 0),
            })

        return {
            "team_name":        team_meta.get("name", f"Team {team_id}"),
            # Private classic leagues (league_type "x"), for the mini-league view
            "leagues": [
                {"id": lg["id"], "name": lg.get("name", ""), "rank": lg.get("entry_rank")}
                for lg in team_meta.get("leagues", {}).get("classic", [])
                if lg.get("league_type") == "x"
            ],
            "manager_name":     f"{team_meta.get('player_first_name','')} {team_meta.get('player_last_name','')}".strip(),
            "overall_points":   team_meta.get("summary_overall_points", 0),
            "overall_rank":     team_meta.get("summary_overall_rank", 0),
            "gameweek_points":  team_meta.get("summary_event_points", 0),
            "bank":             team_meta.get("last_deadline_bank", 0) / 10,
            "team_value":       team_meta.get("last_deadline_value", 0) / 10,
            "transfers_this_gw": picks_data.get("entry_history", {}).get("event_transfers", 0),
            "active_chip":      picks_data.get("active_chip"),
            "picks":            enriched,
            "gameweek":         gw_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching FPL team {team_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Could not load team {team_id}. Ensure the team ID is correct."
        )


@router.get("/{team_id}/transfers")
async def suggest_transfers(
    team_id:       int,
    max_hits:      int = Query(0, ge=0, le=4, description="Transfer point hits to allow"),
    data_service:  FPLDataService   = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:          dict             = Depends(get_current_user),
):
    """
    Suggest the best 1-free-transfer swap for an FPL team.
    Returns ranked list of sell/buy pairs sorted by predicted points improvement.
    """
    # Open to all users during launch — flip require_pro(user) back on later.
    try:
        # Fetch team (pass user so require_pro inside doesn't re-check)
        team_data = await get_fpl_team(team_id, data_service=data_service, user=user)
        picks = team_data["picks"]
        starting = [p for p in picks if p["is_starting"]]

        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams_map = {t["id"]: t for t in bootstrap.get("teams", [])}
        pos_map   = {p["id"]: p for p in bootstrap.get("element_types", [])}

        await prediction_service.ensure_ready(data_service)

        # Build prediction map for all players (single vectorised pass)
        _preds = prediction_service.predict_batch(elements, "xp")
        pred_map = {p["id"]: max(0.0, v) for p, v in zip(elements, _preds)}

        squad_ids = {p["id"] for p in picks}
        bank = team_data.get("bank", 0.0)

        suggestions = []
        for sell_player in starting:
            sell_id    = sell_player["id"]
            sell_pred  = pred_map.get(sell_id, 0)
            sell_price = sell_player["price"]
            sell_pos   = sell_player["position"]
            available_budget = sell_price + bank

            for candidate in elements:
                cand_id = candidate["id"]
                if cand_id in squad_ids:
                    continue
                if candidate.get("element_type", 0) != sell_pos:
                    continue
                cand_price = float(candidate.get("now_cost", 0)) / 10
                if cand_price > available_budget:
                    continue
                chance = candidate.get("chance_of_playing_next_round")
                if chance is not None and chance < 50:
                    continue

                cand_pred  = pred_map.get(cand_id, 0)
                improvement = cand_pred - sell_pred
                if improvement < 0.3:
                    continue

                team = teams_map.get(candidate.get("team", 0), {})
                pos  = pos_map.get(sell_pos, {})
                suggestions.append({
                    "sell": {
                        "id":               sell_id,
                        "name":             sell_player["name"],
                        "price":            sell_price,
                        "predicted_points": round(sell_pred, 1),
                        "team_name":        sell_player["team_name"],
                        "position_name":    sell_player["position_name"],
                    },
                    "buy": {
                        "id":               cand_id,
                        "name":             candidate.get("web_name", ""),
                        "price":            cand_price,
                        "predicted_points": round(cand_pred, 1),
                        "team_name":        team.get("name", ""),
                        "position_name":    pos.get("singular_name_short", ""),
                        "form":             float(candidate.get("form", 0)),
                        "ownership":        float(candidate.get("selected_by_percent", 0)),
                    },
                    "improvement": round(improvement, 1),
                    "price_diff":  round(cand_price - sell_price, 1),
                })

        # Deduplicate: only best swap per target player
        suggestions.sort(key=lambda x: x["improvement"], reverse=True)
        seen_buys = set()
        deduped = []
        for s in suggestions:
            bid = s["buy"]["id"]
            if bid not in seen_buys:
                seen_buys.add(bid)
                deduped.append(s)

        return {
            "suggestions":  deduped[:8],
            "team_id":      team_id,
            "gameweek":     team_data["gameweek"],
            "bank":         bank,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transfer suggestion error for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Transfer suggestion failed")


@router.get("/{team_id}/plan")
async def plan_transfers(
    team_id:        int,
    free_transfers: Optional[int] = Query(None, ge=0, le=5,
                                          description="Free transfers available; estimated from history if omitted"),
    max_transfers:  int = Query(3, ge=0, le=5),
    data_service:   FPLDataService    = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:           dict              = Depends(get_current_user),
):
    """
    Best transfers to make now for the next 3 gameweeks, including whether a
    -4 hit pays for itself, versus holding. Also picks XI and captain per GW.
    """
    team_data = await get_fpl_team(team_id, data_service=data_service, user=user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        by_id     = {e["id"]: e for e in elements}
        teams_map = {t["id"]: t for t in bootstrap.get("teams", [])}
        await prediction_service.ensure_ready(data_service)

        history = None
        try:
            client = await data_service._get_client()
            resp = await client.get(f"https://fantasy.premierleague.com/api/entry/{team_id}/history/")
            resp.raise_for_status()
            history = resp.json()
        except Exception as e:
            logger.warning(f"History fetch failed for {team_id}: {e}")

        estimated = free_transfers is None
        if estimated:
            free_transfers = estimate_free_transfers(history) if history else 1

        current = [p["id"] for p in team_data["picks"]]
        # Current players valued at today's price (selling prices aren't public)
        budget = sum(by_id[i]["now_cost"] for i in current if i in by_id) / 10 + team_data.get("bank", 0.0)
        cands = candidates_from_elements(elements, prediction_service, keep=set(current))
        owned = {c.id for c in cands}
        missing = [i for i in current if i not in owned]
        if missing:
            raise HTTPException(status_code=422, detail="Squad contains players no longer in the game")

        next_gw = prediction_service.xp.next_gw
        chips = chips_available(history or {}, next_gw) if (history and next_gw) else []
        best, hold, wildcard = await asyncio.gather(
            asyncio.to_thread(optimise, cands, budget, current, free_transfers, max_transfers),
            asyncio.to_thread(optimise, cands, budget, current, free_transfers, 0),
            # Wildcard: unlimited free transfers
            asyncio.to_thread(optimise, cands, budget, current, 15, 15)
            if "wildcard" in chips else asyncio.sleep(0, result=None),
        )
        horizon = len(best.lineups)
        xp_of = {c.id: list(c.xp) for c in cands}
        chip_tips = chip_advice(
            best, hold, wildcard.expected_points if wildcard else None,
            [next_gw + i for i in range(horizon)] if next_gw else list(range(1, horizon + 1)),
            {e["id"]: e["team"] for e in elements},
            prediction_service.xp.fixture_counts,
            xp_of,
            chips,
        )

        def player(pid: int) -> dict:
            el = by_id[pid]
            return {
                "id":   pid,
                "name": el.get("web_name", ""),
                "team_name": teams_map.get(el.get("team", 0), {}).get("short_name", ""),
                "position": el.get("element_type"),
                "price": el["now_cost"] / 10,
                "predicted_next_3": prediction_service.horizon(pid),
            }

        gain = round(best.expected_points - hold.expected_points, 2)
        if not best.transfers_in:
            advice = "Hold: no transfer improves your next 3 gameweeks enough. Roll the free transfer."
        elif best.hits:
            advice = (f"Make {len(best.transfers_in)} transfers (-{4 * best.hits} hit): "
                      f"+{gain} expected points over 3 gameweeks after the hit.")
        else:
            advice = f"Make {len(best.transfers_in)} free transfer(s): +{gain} expected points over 3 gameweeks."

        return {
            "team_id":        team_id,
            "gameweek":       prediction_service.xp.next_gw,
            "advice":         advice,
            "free_transfers": free_transfers,
            "free_transfers_estimated": estimated,
            "chips": chip_tips,
            "gain":           gain,
            "hits":           best.hits,
            "transfers_out":  [player(p) for p in best.transfers_out],
            "transfers_in":   [player(p) for p in best.transfers_in],
            "expected_points": {"with_transfers": best.expected_points, "hold": hold.expected_points},
            "per_gameweek":   [
                {"lineup": lineup, "captain": cap, "points": pts,
                 "captain_name": by_id[cap].get("web_name", ""),
                 "captain_xp": round(xp_of[cap][g], 2)}
                for g, (lineup, cap, pts) in enumerate(zip(best.lineups, best.captains, best.per_gw_points))
            ],
            "assumptions": (
                f"{free_transfers} free transfer(s); current players valued at today's price "
                "(your selling price may be lower); bench points weighted 0.1."
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transfer plan error for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Transfer planning failed")


@router.get("/{team_id}/league/{league_id}")
async def mini_league(
    team_id:   int,
    league_id: int,
    rivals:    int = Query(20, ge=1, le=50, description="How many top rivals to compare against"),
    data_service:  FPLDataService     = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:      dict = Depends(get_current_user),
):
    """
    Your team vs your mini-league: effective ownership among the top rivals
    (their latest locked picks), and the players that swing the race next GW.
    """
    gw_info = await data_service.get_gameweek_info()
    cur = gw_info.get("current")
    if not cur:
        raise HTTPException(status_code=400, detail="Rivals' teams are visible after the first deadline")
    gw = cur["id"]
    client = await data_service._get_client()
    base = "https://fantasy.premierleague.com/api"

    resp = await client.get(f"{base}/leagues-classic/{league_id}/standings/")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="League not found")
    resp.raise_for_status()
    standings = resp.json()
    results = standings.get("standings", {}).get("results", [])
    me = next((r for r in results if r["entry"] == team_id), None)
    others = [r for r in results if r["entry"] != team_id][:rivals]

    cache = get_cache_manager()
    sem = asyncio.Semaphore(8)

    async def picks_for(entry: int) -> list:
        key = f"picks:{entry}:{gw}"
        hit = cache.get(key)
        if hit is not None:
            return hit
        async with sem:
            r = await client.get(f"{base}/entry/{entry}/event/{gw}/picks/")
        if r.status_code != 200:
            return []
        picks = r.json().get("picks", [])
        cache.set(key, picks)
        return picks

    mine, *rival_picks = await asyncio.gather(picks_for(team_id), *(picks_for(r["entry"]) for r in others))
    rival_picks = [p for p in rival_picks if p]
    if not mine:
        raise HTTPException(status_code=404, detail="Could not load your picks")

    await prediction_service.ensure_ready(data_service)
    bootstrap = await data_service.get_bootstrap_data()
    by_id = {e["id"]: e for e in bootstrap.get("elements", [])}
    teams_map = {t["id"]: t for t in bootstrap.get("teams", [])}
    xp_next = {el: prediction_service.xp.next_xp(el) or 0.0 for el in by_id}

    view = league_view(mine, rival_picks, xp_next)
    for section in ("threats", "undercovered", "differentials"):
        for row in view[section]:
            el = by_id.get(row["id"], {})
            row["name"] = el.get("web_name", "")
            row["team_name"] = teams_map.get(el.get("team"), {}).get("short_name", "")

    return {
        "league": {"id": league_id, "name": standings.get("league", {}).get("name", "")},
        "gameweek_picks": gw,
        "you": {"rank": me.get("rank") if me else None, "total": me.get("total") if me else None},
        "rivals": [
            {"entry": r["entry"], "name": r.get("entry_name", ""), "manager": r.get("player_name", ""),
             "rank": r.get("rank"), "total": r.get("total"),
             "gap": (r.get("total", 0) - me.get("total", 0)) if me else None}
            for r in others
        ],
        **view,
        "method": "Effective ownership = average pick multiplier among these rivals (captain counts 2). "
                  "Swing = next-GW xP x (your multiplier - league EO).",
    }


# ── Briefing ──────────────────────────────────────────────────────────────────

# Squad alert categories returned in the briefing.
_FLAG_INJURED = "INJURED"        # ruled out / chance of playing < 25
_FLAG_DOUBT   = "DOUBT"          # 25 ≤ chance < 75 or has news
_FLAG_PRICE_DROP = "PRICE_DROP"  # cost dropped this gameweek

# Free-tier briefing meter: how many cache-miss briefing fetches per gameweek.
# Pro/founder bypass entirely. Cache hits don't count.
_FREE_BRIEFINGS_PER_GW = int(os.getenv("FREE_BRIEFINGS_PER_GW", "1"))


def _squad_alerts(picks: list[dict]) -> list[dict]:
    """Extract injury/doubt/price-drop alerts for the user's XI only."""
    alerts: list[dict] = []
    for p in picks:
        if not p.get("is_starting"):
            continue
        chance = p.get("chance_of_playing")
        news   = (p.get("news") or "").strip()

        flag = None
        if chance is not None and chance < 25:
            flag = _FLAG_INJURED
        elif (chance is not None and chance < 75) or news:
            flag = _FLAG_DOUBT

        if flag:
            alerts.append({
                "player_id":     p["id"],
                "name":          p["name"],
                "team_name":     p.get("team_name", ""),
                "position_name": p.get("position_name", ""),
                "flag":          flag,
                "chance":        chance,
                "news":          news,
            })

    # Price-drop risk uses the raw element field, fetched separately by caller.
    return alerts


def _has_unlimited_briefings(user: dict) -> bool:
    """Pro/founder users — and *anyone* during the launch grace period — get
    unlimited briefings. Free signed-in users post-grace are metered."""
    return get_effective_plan(user) in ("pro", "founder")


def _briefing_meter_check_and_increment(
    user: dict, gw_id: int, team_id: int
) -> tuple[bool, int]:
    """
    Returns (allowed, used_count) for this user/gameweek.

    Anonymous users post-grace: not allowed (must sign in to use the meter).
    Signed-in free users post-grace: up to _FREE_BRIEFINGS_PER_GW distinct
    teams per GW. Re-opening a team already briefed this GW is free, so the
    meter counts teams rather than page loads. Runs in a Firestore transaction
    so parallel requests can't both slip under the limit.
    """
    if _has_unlimited_briefings(user):
        return (True, 0)

    uid = user.get("uid")
    if not uid:
        return (False, 0)  # anonymous post-grace → must sign in

    db = get_db()
    if db is None:
        # Firestore unavailable — fail open during this transient issue rather
        # than locking everyone out. Log so we notice.
        logger.warning("Briefing meter: Firestore unavailable, failing open")
        return (True, 0)

    try:
        from firebase_admin import firestore

        doc_ref = db.collection("users").document(uid)

        @firestore.transactional
        def _txn(transaction) -> tuple[bool, int]:
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else {}
            teams_by_gw = data.get("briefing_teams") or {}
            teams = [int(t) for t in teams_by_gw.get(str(gw_id), [])]
            if team_id in teams:
                return (True, len(teams))
            if len(teams) >= _FREE_BRIEFINGS_PER_GW:
                return (False, len(teams))
            teams_by_gw[str(gw_id)] = teams + [team_id]
            transaction.set(doc_ref, {"briefing_teams": teams_by_gw}, merge=True)
            return (True, len(teams) + 1)

        return _txn(db.transaction())
    except Exception as e:
        logger.warning(f"Briefing meter Firestore op failed: {e} — failing open")
        return (True, 0)


def _captain_pick(picks: list[dict], pred_map: dict[int, float]) -> dict | None:
    """Highest predicted-points starter. Returns None if XI is empty."""
    starters = [p for p in picks if p.get("is_starting")]
    if not starters:
        return None
    best = max(starters, key=lambda p: pred_map.get(p["id"], 0.0))
    current = next((p for p in starters if p.get("is_captain")), None)
    return {
        "player_id":           best["id"],
        "name":                best["name"],
        "team_name":           best.get("team_name", ""),
        "predicted_points":    round(pred_map.get(best["id"], 0.0), 1),
        "currently_captained": bool(best.get("is_captain")),
        "current_captain": (
            None if current is None else {
                "player_id":        current["id"],
                "name":             current["name"],
                "predicted_points": round(pred_map.get(current["id"], 0.0), 1),
            }
        ),
    }


def _advice_gameweek(gw_info: dict, now: Optional[datetime] = None) -> dict:
    """
    Pick the gameweek a briefing should talk about. Mid-gameweek FPL still
    reports the one in play as "current", but the captain and transfer advice
    is for the next deadline, so once the current deadline has passed we label
    the briefing with the next event.
    """
    cur = gw_info.get("current") or gw_info.get("next") or {}
    nxt = gw_info.get("next")
    dl = cur.get("deadline_time")
    if nxt and dl:
        try:
            passed = datetime.fromisoformat(dl.replace("Z", "+00:00")) <= (now or datetime.now(timezone.utc))
        except ValueError:
            passed = False
        if passed:
            return nxt
    return cur


@router.get("/{team_id}/briefing")
async def get_team_briefing(
    team_id:           int,
    data_service:      FPLDataService    = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:              dict              = Depends(get_current_user),
):
    """
    Personalised "what should I do today" card for an FPL team.

    Composes squad + flags + captain pick + top-1 transfer + LLM-written reasons
    into a single payload — the goal is one HTTP round-trip from the frontend.

    Cached per (team_id, gameweek_id) for 5 min so a returning visitor doesn't
    re-trigger the Gemini call.
    """
    cache = get_cache_manager()

    try:
        team_data = await get_fpl_team(team_id, data_service=data_service, user=user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Briefing: team fetch failed for {team_id}: {e}")
        raise HTTPException(status_code=404, detail="Team not found")

    gw_id = team_data["gameweek"]

    # Meter check (post-grace only) runs before the cache: the cache is shared
    # across users, so a hit must not let a free user read someone else's
    # briefing for nothing.
    allowed, used = _briefing_meter_check_and_increment(user, gw_id, team_id)
    if not allowed:
        # Return a 200 with a paywall payload so the frontend renders an
        # upgrade card cleanly, not a generic error.
        is_anon = not user.get("uid")
        return {
            "team_id":     team_id,
            "gameweek":    gw_id,
            "paywall":     True,
            "reason":      "anon" if is_anon else "limit_reached",
            "free_used":   used,
            "free_limit":  _FREE_BRIEFINGS_PER_GW,
            "message": (
                "Sign in with Google to unlock your free briefing each gameweek."
                if is_anon else
                f"You've used your free briefing for GW{gw_id}. "
                f"Upgrade to Pro for unlimited refreshes when team news drops."
            ),
            "upgrade_url": "/api/payments/initialize",
            "upgrade_plan_id": "pro",
        }

    cache_key = f"briefing:{team_id}:{gw_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    picks = team_data["picks"]

    # Build prediction map for the XI in one batched call (vectorised).
    bootstrap = await data_service.get_bootstrap_data()
    elements_by_id = {p["id"]: p for p in bootstrap.get("elements", [])}
    await prediction_service.ensure_ready(data_service)

    starting_elements = [elements_by_id[p["id"]] for p in picks if p.get("is_starting") and p["id"] in elements_by_id]
    starting_preds    = prediction_service.predict_batch(starting_elements, "xp")
    pred_map = {p["id"]: float(v) for p, v in zip(starting_elements, starting_preds)}

    # Alerts + price-drop overlay (price-drop pulled from the raw FPL element)
    alerts = _squad_alerts(picks)
    for p in picks:
        if not p.get("is_starting"):
            continue
        raw = elements_by_id.get(p["id"], {})
        cost_change = int(raw.get("cost_change_event", 0) or 0)
        if cost_change < 0 and not any(a["player_id"] == p["id"] for a in alerts):
            alerts.append({
                "player_id":     p["id"],
                "name":          p["name"],
                "team_name":     p.get("team_name", ""),
                "position_name": p.get("position_name", ""),
                "flag":          _FLAG_PRICE_DROP,
                "chance":        p.get("chance_of_playing"),
                "news":          f"Price dropped {cost_change/10:+.1f}m this gameweek",
            })

    captain = _captain_pick(picks, pred_map)

    # One transfer suggestion — reuse the existing logic, take the top.
    top_transfer = None
    try:
        transfers = await suggest_transfers(
            team_id, max_hits=0,
            data_service=data_service,
            prediction_service=prediction_service,
            user=user,
        )
        sugg = (transfers or {}).get("suggestions") or []
        if sugg:
            top_transfer = sugg[0]
    except HTTPException as e:
        # Pro-only or other gating shouldn't kill the briefing
        logger.info(f"Briefing transfer fetch skipped (status {e.status_code})")
    except Exception as e:
        logger.warning(f"Briefing transfer fetch failed: {e}")

    # The gameweek this advice is for: the next deadline, not the one that just passed
    gw_info = await data_service.get_gameweek_info()
    advice_gw = _advice_gameweek(gw_info)
    deadline = advice_gw.get("deadline_time")
    if advice_gw.get("id"):
        gw_id = advice_gw["id"]

    # Gemini reasons (cheap call, never fatal). Pass enough comparative data
    # (form, current captain, ownership) for the model to write *insight*
    # rather than paraphrase what's in the input.
    def _player_meta(player_id: int) -> dict:
        e = elements_by_id.get(player_id, {})
        return {
            "form":             float(e.get("form", 0) or 0),
            "ownership":        float(e.get("selected_by_percent", 0) or 0),
            "minutes":          int(e.get("minutes", 0) or 0),
            "goals":            int(e.get("goals_scored", 0) or 0),
            "assists":          int(e.get("assists", 0) or 0),
        }

    llm_input_alerts = [
        {
            "player_id":     a["player_id"],
            "name":          a["name"],
            "team":          a["team_name"],
            "flag":          a["flag"],
            "chance":        a["chance"],
            "news":          a["news"],
            **_player_meta(a["player_id"]),
        }
        for a in alerts
    ]
    llm_input_captain = (
        None if captain is None else {
            "name":             captain["name"],
            "team":             captain["team_name"],
            "predicted_points": captain["predicted_points"],
            "currently_captained": captain["currently_captained"],
            **_player_meta(captain["player_id"]),
            "current_captain": (
                None if not captain.get("current_captain") else {
                    "name":             captain["current_captain"]["name"],
                    "predicted_points": captain["current_captain"]["predicted_points"],
                    **_player_meta(captain["current_captain"]["player_id"]),
                }
            ),
        }
    )
    llm_input_transfer = (
        None if top_transfer is None else {
            "sell": {
                **top_transfer["sell"],
                **_player_meta(top_transfer["sell"]["id"]),
            },
            "buy": {
                **top_transfer["buy"],
                **_player_meta(top_transfer["buy"]["id"]),
            },
            "improvement": top_transfer["improvement"],
        }
    )

    reasons = gemini_service.generate_briefing_reasons(
        team_name=team_data.get("team_name", ""),
        alerts=llm_input_alerts,
        captain=llm_input_captain,
        transfer=llm_input_transfer,
    )

    # Stitch reasons back into the structured payload
    if captain and reasons.get("captain_reason"):
        captain["reason"] = reasons["captain_reason"]
    if top_transfer and reasons.get("transfer_reason"):
        top_transfer = {**top_transfer, "reason": reasons["transfer_reason"]}
    alert_reasons_map = reasons.get("alert_reasons") or {}
    for a in alerts:
        r = alert_reasons_map.get(str(a["player_id"]))
        if r:
            a["reason"] = r

    payload = {
        "team_id":          team_id,
        "team_name":        team_data.get("team_name"),
        "manager_name":     team_data.get("manager_name"),
        "gameweek":         gw_id,
        "deadline":         deadline,
        "summary":          reasons.get("summary", ""),
        "alerts":           alerts,
        "captain":          captain,
        "top_transfer":     top_transfer,
        "ai_reasons":       gemini_service.is_available(),
        "data_fetched_at":  datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, payload)
    return payload
