"""
Teams API Router
Endpoints for team data, squad optimisation, and fixture difficulty ratings.
"""

import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
from ..services.optimizer import candidates_from_elements, optimise
from ..services.prediction_service import PredictionService, get_prediction_service
from ..auth.firebase_auth import get_current_user, require_pro

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
        current_gw = next(
            (e for e in events if e.get("is_current") or e.get("is_next")), {}
        )
        current_gw_id = current_gw.get("id", 1)

        upcoming_gw_ids = [
            e["id"] for e in events
            if e.get("id", 0) >= current_gw_id
        ][:gameweeks]

        # Fetch all fixtures (upcoming only, then filter by GW)
        all_fixtures = await data_service.get_fixtures(filter_type="upcoming")

        teams_by_id   = {t["id"]: t for t in teams_list}
        fdr: Dict[int, dict] = {}
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


@router.post("/optimize")
async def optimize_squad(
    request:           Dict[str, Any]     = {},
    data_service:      FPLDataService     = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
):
    """
    Best 15-player squad for a budget over the next 3 gameweeks: integer
    programme over the xP model with FPL's squad, club and formation rules.
    """
    try:
        budget = float(request.get("budget", 100.0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="budget must be a number")

    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        by_id     = {e["id"]: e for e in elements}
        await prediction_service.ensure_ready(data_service)

        cands = candidates_from_elements(elements, prediction_service)
        try:
            plan = await asyncio.to_thread(optimise, cands, budget)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"No valid 15-man squad fits a £{budget:.1f}m budget")

        pos_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
        xp_next = {c.id: c.xp[0] for c in cands}
        starting = set(plan.lineups[0])
        squad = []
        for pid in sorted(plan.squad, key=lambda i: (by_id[i]["element_type"], i not in starting)):
            el = by_id[pid]
            squad.append({
                "id":               pid,
                "name":             el.get("web_name", "Unknown"),
                "team":             teams.get(el.get("team", 0), {}).get("name", "Unknown"),
                "position":         pos_map[el["element_type"]],
                "price":            el["now_cost"] / 10,
                "predicted_points": round(xp_next.get(pid, 0.0), 1),
                "predicted_next_3": prediction_service.horizon(pid),
                "form":             float(el.get("form", 0)),
                "ownership":        float(el.get("selected_by_percent", 0)),
                "is_starting":      pid in starting,
                "is_captain":       pid == plan.captains[0],
            })

        counts = {"DEF": 0, "MID": 0, "FWD": 0}
        for p in squad:
            if p["is_starting"] and p["position"] in counts:
                counts[p["position"]] += 1

        return {
            "squad":            squad,
            "total_cost":       plan.cost,
            "remaining_budget": round(budget - plan.cost, 1),
            "predicted_points": plan.per_gw_points[0],
            "predicted_points_horizon": plan.expected_points,
            "per_gameweek":     plan.per_gw_points,
            "captains":         plan.captains,
            "formation":        f"{counts['DEF']}-{counts['MID']}-{counts['FWD']}",
            "method":           "Integer programme over model xP for the next 3 gameweeks "
                                "(captain doubled, bench weighted 0.1).",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Squad optimisation error: {e}")
        raise HTTPException(status_code=500, detail="Squad optimisation failed")
