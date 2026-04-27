"""
FPL Team Import API
Fetch a user's live FPL team by team ID and suggest optimal transfers.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
from ..services.prediction_service import PredictionService, get_prediction_service
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
    require_pro(user)
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
    require_pro(user)
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

        # Build prediction map for all players
        pred_map = {p["id"]: max(0.0, prediction_service.predict(p)) for p in elements}

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
