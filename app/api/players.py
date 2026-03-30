"""
Players API Router
Endpoints for player data, search, predictions, injuries, captain picks,
differentials, price movers, and value analysis.
"""

import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.data_service import FPLDataService, get_data_service
from ..services.prediction_service import PredictionService, get_prediction_service
from ..auth.firebase_auth import get_current_user, plan_limits, require_pro

logger = logging.getLogger(__name__)
router = APIRouter()

POS_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def _enrich(player, teams, positions, prediction_service=None, model_type="random_forest"):
    """Build a standardised player dict from raw FPL element"""
    team = teams.get(player.get("team", 0), {})
    pos  = positions.get(player.get("element_type", 0), {})
    pred = prediction_service.predict(player, model_type) if prediction_service else None
    return {
        "id":               player["id"],
        "name":             player.get("web_name", ""),
        "full_name":        f"{player.get('first_name','')} {player.get('second_name','')}".strip(),
        "team_name":        team.get("name", "Unknown"),
        "team_short":       team.get("short_name", ""),
        "position":         player.get("element_type", 0),
        "position_name":    pos.get("singular_name_short", ""),
        "price":            float(player.get("now_cost", 0)) / 10,
        "form":             min(10.0, float(player.get("form", 0))),
        "ownership":        float(player.get("selected_by_percent", 0)),
        "total_points":     int(player.get("total_points", 0)),
        "points_per_game":  float(player.get("points_per_game", 0)),
        "ict_index":        float(player.get("ict_index", 0)),
        "predicted_points": round(max(0.0, pred), 1) if pred is not None else None,
        "confidence":       0.80,
        "ai_enhanced":      False,
    }


# ── Predictions ───────────────────────────────────────────────────────────────

@router.get("/predictions")
async def get_player_predictions(
    top_n:       int            = Query(20, ge=1, le=100),
    position:    Optional[int]  = Query(None),
    model_type:  str            = Query("basic"),
    data_service: FPLDataService   = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:        dict           = Depends(get_current_user),
):
    """Top predicted players for the next gameweek"""
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        if model_type != "basic" and not prediction_service._trained:
            prediction_service.train(elements)

        predictions = []
        for player in elements:
            if position and player.get("element_type") != position:
                continue
            d = _enrich(player, teams, positions, prediction_service, model_type)
            d["ai_enhanced"] = model_type != "basic"
            predictions.append(d)

        predictions.sort(key=lambda x: x["predicted_points"] or 0, reverse=True)

        limits     = plan_limits(user["plan"])
        hard_limit = min(top_n, limits["predictions_limit"])
        locked_out = len(predictions) - hard_limit if len(predictions) > hard_limit else 0

        return {
            "predictions":    predictions[:hard_limit],
            "total_players":  len(predictions),
            "model_type":     model_type,
            "plan":           user["plan"],
            "locked_count":   locked_out,
        }
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch predictions")


# ── Captain picks ─────────────────────────────────────────────────────────────

@router.get("/captain")
async def get_captain_picks(
    top_n:       int = Query(5, le=10),
    data_service: FPLDataService   = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:        dict = Depends(get_current_user),
):
    """Top captain recommendations for the current gameweek — Pro only"""
    require_pro(user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}
        events    = bootstrap.get("events", [])

        if not prediction_service._trained:
            prediction_service.train(elements)

        # Get current / next GW id
        cur_gw = next((e for e in events if e.get("is_current") or e.get("is_next")), {})
        gw_id  = cur_gw.get("id", 1)

        # Fetch upcoming fixtures to add fixture context
        fixtures = await data_service.get_fixtures(filter_type="upcoming")
        gw_fixtures = [f for f in fixtures if f.get("event") == gw_id]
        # Map team_id -> fixture difficulty + opponent
        fix_map: dict = {}
        for f in gw_fixtures:
            fix_map[f["team_h"]] = {"opponent": teams.get(f["team_a"], {}).get("short_name", ""), "is_home": True,  "difficulty": f.get("team_h_difficulty", 3)}
            fix_map[f["team_a"]] = {"opponent": teams.get(f["team_h"], {}).get("short_name", ""), "is_home": False, "difficulty": f.get("team_a_difficulty", 3)}

        picks = []
        for player in elements:
            # Only outfield + playing players
            if player.get("element_type", 0) == 1:
                continue
            chance = player.get("chance_of_playing_next_round")
            if chance is not None and chance < 50:
                continue

            d = _enrich(player, teams, positions, prediction_service)
            team_fix = fix_map.get(player.get("team", 0), {})
            d["fixture_opponent"] = team_fix.get("opponent", "")
            d["fixture_is_home"]  = team_fix.get("is_home", True)
            d["fixture_difficulty"] = team_fix.get("difficulty", 3)
            picks.append(d)

        picks.sort(key=lambda x: x["predicted_points"] or 0, reverse=True)
        return {
            "captain_picks": picks[:top_n],
            "gameweek": gw_id,
        }
    except Exception as e:
        logger.error(f"Error fetching captain picks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch captain picks")


# ── Trending players ─────────────────────────────────────────────────────────

@router.get("/trending")
async def get_trending(
    top_n: int = Query(12, le=30),
    data_service: FPLDataService = Depends(get_data_service),
):
    """Most transferred in and out this gameweek — free endpoint"""
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        def fmt(p):
            team = teams.get(p.get("team", 0), {})
            pos  = positions.get(p.get("element_type", 0), {})
            return {
                "id":            p["id"],
                "name":          p.get("web_name", ""),
                "team_name":     team.get("name", ""),
                "team_short":    team.get("short_name", ""),
                "position_name": pos.get("singular_name_short", ""),
                "price":         float(p.get("now_cost", 0)) / 10,
                "form":          float(p.get("form", 0)),
                "ownership":     float(p.get("selected_by_percent", 0)),
                "transfers_in":  int(p.get("transfers_in_event", 0)),
                "transfers_out": int(p.get("transfers_out_event", 0)),
                "price_change":  p.get("cost_change_event", 0) / 10,
                "total_points":  int(p.get("total_points", 0)),
                "news":          p.get("news", ""),
            }

        active = [p for p in elements if float(p.get("minutes", 0)) > 0]
        trending_in  = sorted(active, key=lambda x: int(x.get("transfers_in_event",  0)), reverse=True)[:top_n]
        trending_out = sorted(active, key=lambda x: int(x.get("transfers_out_event", 0)), reverse=True)[:top_n]

        return {
            "trending_in":  [fmt(p) for p in trending_in],
            "trending_out": [fmt(p) for p in trending_out],
        }
    except Exception as e:
        logger.error(f"Trending error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending data")


# ── 3-GW Fixture Planner ──────────────────────────────────────────────────────

@router.get("/three-gw")
async def get_three_gw_picks(
    top_n: int = Query(20, le=50),
    position: Optional[int] = Query(None),
    data_service: FPLDataService = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user: dict = Depends(get_current_user),
):
    """Best players ranked by predicted points across next 3 gameweeks — Pro only"""
    require_pro(user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}
        events    = bootstrap.get("events", [])

        if not prediction_service._trained:
            prediction_service.train(elements)

        # Find next 3 upcoming GW ids
        upcoming = [e for e in events if not e.get("finished", True)][:3]
        gw_ids   = [e["id"] for e in upcoming]

        if not gw_ids:
            raise HTTPException(status_code=404, detail="No upcoming gameweeks found")

        # Fetch fixtures for those GWs
        all_fixtures = await data_service.get_fixtures(filter_type="upcoming")
        gw_fixtures  = [f for f in all_fixtures if f.get("event") in gw_ids]

        # Build fixture map: team_id → list of {gw, difficulty, is_home, opponent}
        fix_map: dict = {}
        for f in gw_fixtures:
            h, a = f["team_h"], f["team_a"]
            fix_map.setdefault(h, []).append({
                "gw": f["event"], "difficulty": f.get("team_h_difficulty", 3),
                "is_home": True,  "opponent": teams.get(a, {}).get("short_name", "?"),
            })
            fix_map.setdefault(a, []).append({
                "gw": f["event"], "difficulty": f.get("team_a_difficulty", 3),
                "is_home": False, "opponent": teams.get(h, {}).get("short_name", "?"),
            })

        # Difficulty multiplier: easy fixture boosts predicted points
        diff_mult = {1: 1.30, 2: 1.15, 3: 1.00, 4: 0.85, 5: 0.70}

        picks = []
        for player in elements:
            if position and player.get("element_type") != position:
                continue
            chance = player.get("chance_of_playing_next_round")
            if chance is not None and chance < 50:
                continue
            if float(player.get("minutes", 0)) == 0:
                continue

            base_pred   = prediction_service.predict(player, "ensemble")
            team_id     = player.get("team", 0)
            fixtures    = fix_map.get(team_id, [])
            fixtures    = sorted(fixtures, key=lambda x: x["gw"])[:3]

            gw_scores = []
            for fx in fixtures:
                mult  = diff_mult.get(fx["difficulty"], 1.0)
                score = max(0, base_pred * mult)
                gw_scores.append({
                    "gw":         fx["gw"],
                    "opponent":   fx["opponent"],
                    "is_home":    fx["is_home"],
                    "difficulty": fx["difficulty"],
                    "predicted":  round(score, 1),
                })

            three_gw_total = sum(s["predicted"] for s in gw_scores)
            if not gw_scores:
                continue

            d = _enrich(player, teams, positions, prediction_service, "ensemble")
            d["three_gw_total"] = round(three_gw_total, 1)
            d["three_gw_avg"]   = round(three_gw_total / len(gw_scores), 1)
            d["fixtures"]       = gw_scores
            picks.append(d)

        picks.sort(key=lambda x: x["three_gw_total"], reverse=True)
        return {
            "picks":       picks[:top_n],
            "gameweeks":   gw_ids,
            "total_found": len(picks),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"3-GW planner error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate 3-GW plan")


# ── Injury / availability ─────────────────────────────────────────────────────

@router.get("/injuries")
async def get_injuries(
    data_service: FPLDataService = Depends(get_data_service),
):
    """Players with injury news or reduced availability"""
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        injured = []
        for player in elements:
            chance = player.get("chance_of_playing_next_round")
            news   = player.get("news", "")
            if not news and (chance is None or chance >= 100):
                continue

            d = _enrich(player, teams, positions)
            d["news"]               = news
            d["news_added"]         = player.get("news_added", "")
            d["chance_next_round"]  = chance  # null=100%, or 0/25/50/75
            d["chance_this_round"]  = player.get("chance_of_playing_this_round")

            # Severity: 0=out, 1=doubt, 2=75% chance
            if chance == 0:
                d["status"] = "out"
            elif chance is not None and chance <= 50:
                d["status"] = "doubt"
            else:
                d["status"] = "monitor"

            injured.append(d)

        injured.sort(key=lambda x: x["ownership"], reverse=True)
        return {"injuries": injured, "count": len(injured)}

    except Exception as e:
        logger.error(f"Error fetching injuries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch injury data")


# ── Differentials ─────────────────────────────────────────────────────────────

@router.get("/differentials")
async def get_differentials(
    max_ownership:    float = Query(8.0, description="Max ownership % to qualify"),
    top_n:            int   = Query(15, le=30),
    data_service:     FPLDataService   = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:             dict  = Depends(get_current_user),
):
    """Low-ownership players with high predicted points — Pro only"""
    require_pro(user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        if not prediction_service._trained:
            prediction_service.train(elements)

        diffs = []
        for player in elements:
            ownership = float(player.get("selected_by_percent", 0))
            if ownership > max_ownership:
                continue
            chance = player.get("chance_of_playing_next_round")
            if chance is not None and chance < 50:
                continue
            d = _enrich(player, teams, positions, prediction_service)
            diffs.append(d)

        diffs.sort(key=lambda x: x["predicted_points"] or 0, reverse=True)
        return {
            "differentials": diffs[:top_n],
            "max_ownership":  max_ownership,
        }
    except Exception as e:
        logger.error(f"Error fetching differentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch differentials")


# ── Price movers ──────────────────────────────────────────────────────────────

@router.get("/price-movers")
async def get_price_movers(
    data_service: FPLDataService = Depends(get_data_service),
    user:         dict           = Depends(get_current_user),
):
    """Players with price changes this gameweek — Pro only"""
    require_pro(user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        rising  = []
        falling = []

        for player in elements:
            change = player.get("cost_change_event", 0)
            if change == 0:
                continue

            team = teams.get(player.get("team", 0), {})
            pos  = positions.get(player.get("element_type", 0), {})
            record = {
                "id":               player["id"],
                "name":             player.get("web_name", ""),
                "team_name":        team.get("name", ""),
                "position_name":    pos.get("singular_name_short", ""),
                "price":            float(player.get("now_cost", 0)) / 10,
                "price_change":     change / 10,          # in £m
                "change_start":     player.get("cost_change_start", 0) / 10,
                "ownership":        float(player.get("selected_by_percent", 0)),
                "transfers_in":     int(player.get("transfers_in_event", 0)),
                "transfers_out":    int(player.get("transfers_out_event", 0)),
                "form":             float(player.get("form", 0)),
            }
            if change > 0:
                rising.append(record)
            else:
                falling.append(record)

        rising.sort(key=lambda x: x["transfers_in"], reverse=True)
        falling.sort(key=lambda x: x["transfers_out"], reverse=True)

        return {
            "rising":  rising[:15],
            "falling": falling[:15],
        }
    except Exception as e:
        logger.error(f"Error fetching price movers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price movers")


# ── Value picks ───────────────────────────────────────────────────────────────

@router.get("/value")
async def get_value_picks(
    top_n:       int = Query(20, le=50),
    data_service: FPLDataService   = Depends(get_data_service),
    prediction_service: PredictionService = Depends(get_prediction_service),
    user:        dict = Depends(get_current_user),
):
    """Best value players — Pro only"""
    require_pro(user)
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        if not prediction_service._trained:
            prediction_service.train(elements)

        values = []
        for player in elements:
            price = float(player.get("now_cost", 0)) / 10
            if price < 4.0:
                continue
            chance = player.get("chance_of_playing_next_round")
            if chance is not None and chance < 50:
                continue
            d = _enrich(player, teams, positions, prediction_service)
            d["value_score"] = round((d["predicted_points"] or 0) / max(price, 0.1), 2)
            values.append(d)

        values.sort(key=lambda x: x["value_score"], reverse=True)
        return {"value_picks": values[:top_n]}

    except Exception as e:
        logger.error(f"Error fetching value picks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch value picks")


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_players(
    q:           str = Query(..., min_length=2),
    data_service: FPLDataService = Depends(get_data_service),
):
    """Search players by name"""
    try:
        bootstrap = await data_service.get_bootstrap_data()
        elements  = bootstrap.get("elements", [])
        teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
        positions = {p["id"]: p for p in bootstrap.get("element_types", [])}

        query = q.lower()
        results = []
        for player in elements:
            full  = f"{player.get('first_name','')} {player.get('second_name','')}".lower()
            short = player.get("web_name", "").lower()
            if query in full or query in short:
                team = teams.get(player.get("team", 0), {})
                pos  = positions.get(player.get("element_type", 0), {})
                results.append({
                    "id":            player["id"],
                    "name":          player.get("web_name", ""),
                    "full_name":     full.title(),
                    "team_name":     team.get("name", "Unknown"),
                    "position_name": pos.get("singular_name_short", ""),
                    "price":         float(player.get("now_cost", 0)) / 10,
                    "total_points":  int(player.get("total_points", 0)),
                    "form":          float(player.get("form", 0)),
                    "ownership":     float(player.get("selected_by_percent", 0)),
                    "news":          player.get("news", ""),
                    "chance_of_playing": player.get("chance_of_playing_next_round"),
                })

        results.sort(key=lambda x: x["total_points"], reverse=True)
        return {"players": results[:20]}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# ── Individual player ─────────────────────────────────────────────────────────

@router.get("/{player_id}")
async def get_player(
    player_id:   int,
    data_service: FPLDataService = Depends(get_data_service),
):
    player = await data_service.get_player_by_id(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    bootstrap = await data_service.get_bootstrap_data()
    teams     = {t["id"]: t for t in bootstrap.get("teams", [])}
    positions = {p["id"]: p for p in bootstrap.get("element_types", [])}
    team = teams.get(player.get("team", 0), {})
    pos  = positions.get(player.get("element_type", 0), {})

    return {
        "id":              player["id"],
        "name":            player.get("web_name", ""),
        "full_name":       f"{player.get('first_name','')} {player.get('second_name','')}".strip(),
        "team_name":       team.get("name", "Unknown"),
        "position_name":   pos.get("singular_name_short", ""),
        "price":           float(player.get("now_cost", 0)) / 10,
        "total_points":    int(player.get("total_points", 0)),
        "points_per_game": float(player.get("points_per_game", 0)),
        "form":            float(player.get("form", 0)),
        "ownership":       float(player.get("selected_by_percent", 0)),
        "minutes":         int(player.get("minutes", 0)),
        "goals_scored":    int(player.get("goals_scored", 0)),
        "assists":         int(player.get("assists", 0)),
        "news":            player.get("news", ""),
        "ict_index":       float(player.get("ict_index", 0)),
        "history":         player.get("history", []),
        "fixtures":        player.get("fixtures", []),
    }
