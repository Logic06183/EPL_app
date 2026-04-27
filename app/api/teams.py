"""
Teams API Router
Endpoints for team data, squad optimisation, and fixture difficulty ratings.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
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
    """Optimise a 15-player FPL squad within budget constraints"""
    budget = float(request.get("budget", 100.0))

    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}

        if not prediction_service._trained:
            prediction_service.train(elements)

        viable = [
            p for p in elements
            if p.get("now_cost", 0) > 0 and p.get("element_type") in [1, 2, 3, 4]
        ]
        for player in viable:
            pred = prediction_service.predict(player)
            player["_predicted"] = max(pred, 0)
            price = player.get("now_cost", 50) / 10
            player["_value"] = player["_predicted"] / max(price, 0.1)

        viable.sort(key=lambda x: x["_value"], reverse=True)

        formation   = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
        starting_11 = {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2}
        pos_map     = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

        squad     = []
        counts    = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
        remaining = budget

        for player in viable:
            if len(squad) >= 15:
                break
            position = pos_map.get(player.get("element_type", 1), "MID")
            price    = player.get("now_cost", 50) / 10
            team     = teams.get(player.get("team", 0), {})

            if counts[position] < formation[position] and price <= remaining:
                squad.append({
                    "id":               player.get("id"),
                    "name":             player.get("web_name", "Unknown"),
                    "team":             team.get("name", "Unknown"),
                    "position":         position,
                    "price":            price,
                    "predicted_points": round(player["_predicted"], 1),
                    "form":             float(player.get("form", 0)),
                    "ownership":        float(player.get("selected_by_percent", 0)),
                    "is_starting":      counts[position] < starting_11.get(position, 0),
                })
                counts[position] += 1
                remaining -= price

        total_cost      = sum(p["price"] for p in squad)
        predicted_total = sum(p["predicted_points"] for p in squad if p.get("is_starting"))

        return {
            "squad":            squad,
            "total_cost":       round(total_cost, 1),
            "remaining_budget": round(remaining, 1),
            "predicted_points": round(predicted_total, 1),
            "formation":        f"{counts['DEF']}-{counts['MID']}-{counts['FWD']}",
        }

    except Exception as e:
        logger.error(f"Squad optimisation error: {e}")
        raise HTTPException(status_code=500, detail="Squad optimisation failed")
