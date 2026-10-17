"""
Teams API Router
Endpoints for team data, squad optimisation, and fixture difficulty ratings.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth.firebase_auth import get_current_user, require_pro
from ..services.data_service import FPLDataService, get_data_service, planning_gameweek
from ..services.prediction_service import PredictionService, get_prediction_service
from ..services.squad_optimizer import POS_NAME, Candidate, InfeasibleSquad, optimise_squad

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_teams(data_service: FPLDataService = Depends(get_data_service)):
    """Get all Premier League teams"""
    try:
        teams = await data_service.get_teams()
        return {"teams": teams, "count": len(teams)}
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch teams")


@router.get("/fdr")
async def get_fixture_difficulty(
    gameweeks:   int = Query(6, ge=1, le=10, description="Number of upcoming GWs to include"),
    data_service: FPLDataService = Depends(get_data_service),
    user:         dict           = Depends(get_current_user),
):
    """
    Fixture Difficulty Rating heatmap — Pro only.
    Returns a matrix of team → [gw, opponent, difficulty, is_home] for the next N gameweeks.
    Difficulty: 1=very easy … 5=very hard.
    """
    require_pro(user)
    try:
        bootstrap    = await data_service.get_bootstrap_data()
        teams_list   = bootstrap.get("teams", [])
        events       = bootstrap.get("events", [])

        # Determine starting GW
        current_gw = planning_gameweek(events)
        current_gw_id = current_gw.get("id", 1)

        upcoming_gw_ids = [
            e["id"] for e in events
            if e.get("id", 0) >= current_gw_id
        ][:gameweeks]

        # Fetch all fixtures (upcoming only, then filter by GW)
        all_fixtures = await data_service.get_fixtures(filter_type="upcoming", limit=None)

        teams_by_id   = {t["id"]: t for t in teams_list}
        fdr: dict[int, dict] = {}
        for t in teams_list:
            fdr[t["id"]] = {
                "team_name":  t.get("name", ""),
                "short_name": t.get("short_name", ""),
                "fixtures":   [],
            }

        for fixture in all_fixtures:
            gw = fixture.get("event")
            if gw not in upcoming_gw_ids:
                continue
            h_id   = fixture.get("team_h")
            a_id   = fixture.get("team_a")
            h_diff = fixture.get("team_h_difficulty", 3)
            a_diff = fixture.get("team_a_difficulty", 3)

            if h_id in fdr:
                fdr[h_id]["fixtures"].append({
                    "gw":         gw,
                    "opponent":   teams_by_id.get(a_id, {}).get("short_name", "?"),
                    "is_home":    True,
                    "difficulty": h_diff,
                })
            if a_id in fdr:
                fdr[a_id]["fixtures"].append({
                    "gw":         gw,
                    "opponent":   teams_by_id.get(h_id, {}).get("short_name", "?"),
                    "is_home":    False,
                    "difficulty": a_diff,
                })

        # Sort fixtures per team by GW
        teams_fdr = sorted(fdr.values(), key=lambda x: x["team_name"])
        for t in teams_fdr:
            t["fixtures"].sort(key=lambda x: x["gw"])
            # Average difficulty for quick sorting
            diffs = [f["difficulty"] for f in t["fixtures"]]
            t["avg_difficulty"] = round(sum(diffs) / len(diffs), 2) if diffs else 3.0

        teams_fdr.sort(key=lambda x: x["avg_difficulty"])

        return {
            "fdr":         teams_fdr,
            "gameweeks":   upcoming_gw_ids,
            "current_gw":  current_gw_id,
        }

    except Exception as e:
        logger.error(f"FDR error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch fixture difficulty")


def _is_selectable(p: dict) -> bool:
    """Exclude players who can't help: unpriced, transferred out, injured or doubtful (<75%)."""
    if p.get("now_cost", 0) <= 0 or p.get("element_type") not in (1, 2, 3, 4):
        return False
    if p.get("status", "a") in ("u", "n", "s", "i"):  # unavailable, not in squad, suspended, injured
        return False
    chance = p.get("chance_of_playing_next_round")
    return chance is None or chance >= 75


class OptimizeRequest(BaseModel):
    budget: float = Field(100.0, ge=50.0, le=200.0, description="Squad budget in £m")


@router.post("/optimize")
async def optimize_squad(
    request:           OptimizeRequest | None = None,
    data_service:      FPLDataService     = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """Optimise a 15-player FPL squad within budget constraints"""
    budget = (request or OptimizeRequest()).budget

    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}

        await prediction_service.ensure_trained(elements)
        model_type = "ensemble" if prediction_service._trained else "basic"

        viable = [p for p in elements if _is_selectable(p)]
        preds = prediction_service.predict_batch(viable, model_type)
        by_id = {p["id"]: p for p in viable}
        candidates = [
            Candidate(
                id=p["id"], position=p["element_type"], club=p.get("team", 0),
                price=p["now_cost"] / 10, predicted=max(float(pred), 0.0),
            )
            for p, pred in zip(viable, preds, strict=True)
        ]

        try:
            # CPU-bound solve (~1s) — keep the event loop free
            result = await asyncio.to_thread(optimise_squad, candidates, budget)
        except InfeasibleSquad as e:
            raise HTTPException(status_code=422, detail=str(e))

        pred_by_id = {c.id: c.predicted for c in candidates}
        starting   = set(result.starting_ids)
        order      = {1: 0, 2: 1, 3: 2, 4: 3}
        squad = []
        for pid in sorted(result.squad_ids, key=lambda i: (i not in starting, order[by_id[i]["element_type"]], -pred_by_id[i])):
            player = by_id[pid]
            squad.append({
                "id":               pid,
                "name":             player.get("web_name", "Unknown"),
                "team":             teams.get(player.get("team", 0), {}).get("name", "Unknown"),
                "position":         POS_NAME[player["element_type"]],
                "price":            player["now_cost"] / 10,
                "predicted_points": round(pred_by_id[pid], 1),
                "form":             float(player.get("form", 0)),
                "ownership":        float(player.get("selected_by_percent", 0)),
                "is_starting":      pid in starting,
                "is_captain":       pid == result.captain_id,
            })

        xi_counts = {pos: sum(1 for p in squad if p["is_starting"] and p["position"] == pos) for pos in ("DEF", "MID", "FWD")}
        predicted_total = sum(p["predicted_points"] for p in squad if p["is_starting"]) + round(pred_by_id[result.captain_id], 1)

        return {
            "squad":            squad,
            "captain_id":       result.captain_id,
            "total_cost":       result.total_cost,
            "remaining_budget": round(budget - result.total_cost, 1),
            "predicted_points": round(predicted_total, 1),
            "formation":        f"{xi_counts['DEF']}-{xi_counts['MID']}-{xi_counts['FWD']}",
            "model_type":       model_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Squad optimisation error: {e}")
        raise HTTPException(status_code=500, detail="Squad optimisation failed")
