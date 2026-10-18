"""
Mini-league view: what your rivals own that you don't.

Effective ownership (EO) within the league = average pick multiplier across
rival teams (starter 1, captain 2, triple captain 3, bench 0). A player's
"swing" for you next gameweek is xP x (your multiplier - league EO): negative
swing is a threat (they gain on you if he scores), positive is a differential.
"""

from __future__ import annotations

from typing import Dict, List


def league_ownership(rival_picks: List[List[dict]]) -> Dict[int, float]:
    """rival_picks: one FPL picks list per rival ({element, multiplier})."""
    if not rival_picks:
        return {}
    eo: Dict[int, float] = {}
    for picks in rival_picks:
        for p in picks:
            eo[p["element"]] = eo.get(p["element"], 0.0) + float(p.get("multiplier", 0))
    n = len(rival_picks)
    return {el: v / n for el, v in eo.items()}


def league_view(
    my_picks: List[dict], rival_picks: List[List[dict]], xp_next: Dict[int, float], top: int = 8,
) -> dict:
    eo = league_ownership(rival_picks)
    mine = {p["element"]: float(p.get("multiplier", 0)) for p in my_picks}
    swing = {el: xp_next.get(el, 0.0) * (mine.get(el, 0.0) - eo.get(el, 0.0))
             for el in set(eo) | set(mine)}

    threats = sorted((el for el in swing if swing[el] < 0 and el not in mine),
                     key=lambda el: swing[el])[:top]
    undercovered = sorted((el for el in swing if swing[el] < 0 and el in mine),
                          key=lambda el: swing[el])[:top]
    differentials = sorted((el for el in swing if swing[el] > 0),
                           key=lambda el: -swing[el])[:top]

    def row(el: int) -> dict:
        return {"id": el, "league_eo": round(eo.get(el, 0.0), 2), "your_multiplier": mine.get(el, 0.0),
                "xp": round(xp_next.get(el, 0.0), 2), "swing": round(swing[el], 2)}

    return {
        "rivals_compared": len(rival_picks),
        "threats": [row(el) for el in threats],                 # they own, you don't
        "undercovered": [row(el) for el in undercovered],       # you own, but they own more (e.g. captain)
        "differentials": [row(el) for el in differentials],     # you gain if they score
        "net_swing": round(sum(swing.values()), 2),
    }
