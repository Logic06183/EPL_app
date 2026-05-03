"""
FPL Team Import API
Fetch a user's live FPL team by team ID, suggest optimal transfers, and
build a personalised briefing card for the user's squad.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
from ..services.prediction_service import PredictionService, get_prediction_service
from ..services import gemini_service
from ..utils.cache import get_cache_manager
from ..auth.firebase_auth import get_current_user, require_pro

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
            "manager_name":     f"{team_meta.get('player_first_name','')} {team_meta.get('player_last_name','')}".strip(),
            "overall_points":   team_meta.get("summary_overall_points", 0),
            "overall_rank":     team_meta.get("summary_overall_rank", 0),
            "gameweek_points":  team_meta.get("summary_event_points", 0),
            "bank":             team_meta.get("last_deadline_bank", 0) / 10,
            "team_value":       team_meta.get("last_deadline_value", 0) / 10,
            "free_transfers":   picks_data.get("entry_history", {}).get("event_transfers", 0),
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

        if not prediction_service._trained:
            prediction_service.train(elements)

        # Build prediction map for all players (single vectorised pass)
        _preds = prediction_service.predict_batch(elements, "random_forest")
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


# ── Briefing ──────────────────────────────────────────────────────────────────

# Squad alert categories returned in the briefing.
_FLAG_INJURED = "INJURED"        # ruled out / chance of playing < 25
_FLAG_DOUBT   = "DOUBT"          # 25 ≤ chance < 75 or has news
_FLAG_PRICE_DROP = "PRICE_DROP"  # cost dropped this gameweek


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
    cache_key = f"briefing:{team_id}:{gw_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    picks = team_data["picks"]

    # Build prediction map for the XI in one batched call (vectorised).
    bootstrap = await data_service.get_bootstrap_data()
    elements_by_id = {p["id"]: p for p in bootstrap.get("elements", [])}
    if not prediction_service._trained:
        prediction_service.train(list(elements_by_id.values()))

    starting_elements = [elements_by_id[p["id"]] for p in picks if p.get("is_starting") and p["id"] in elements_by_id]
    starting_preds    = prediction_service.predict_batch(starting_elements, "ensemble")
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

    # Gameweek deadline
    gw_info = await data_service.get_gameweek_info()
    cur     = gw_info.get("current") or gw_info.get("next") or {}
    deadline = cur.get("deadline_time")

    # Gemini reasons (cheap call, never fatal)
    llm_input_alerts = [
        {
            "player_id":     a["player_id"],
            "name":          a["name"],
            "team":          a["team_name"],
            "flag":          a["flag"],
            "chance":        a["chance"],
            "news":          a["news"],
        }
        for a in alerts
    ]
    llm_input_captain = (
        None if captain is None else {
            "name":             captain["name"],
            "team":             captain["team_name"],
            "predicted_points": captain["predicted_points"],
            "currently_captained": captain["currently_captained"],
        }
    )
    llm_input_transfer = (
        None if top_transfer is None else {
            "sell":        top_transfer["sell"],
            "buy":         top_transfer["buy"],
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
