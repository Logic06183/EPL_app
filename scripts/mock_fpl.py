"""
Deterministic stand-in for the FPL public API — for demos, offline dev and
full-stack browser tests. Serves the endpoints app/ uses:

  /api/bootstrap-static/   /api/fixtures/   /api/element-summary/{id}/
  /api/entry/{id}/         /api/entry/{id}/event/{gw}/picks/

    python scripts/mock_fpl.py --port 8090
    FPL_API_BASE=http://localhost:8090/api make dev     # or: make demo

8 gameweeks played, GW9 next; 20 clubs × 25 players; team id 1 is a legal squad.
"""

from __future__ import annotations

import argparse
import random
from datetime import UTC, datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException

CLUBS = ["Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley", "Chelsea", "Crystal Palace",
         "Everton", "Fulham", "Leeds", "Liverpool", "Man City", "Man Utd", "Newcastle", "Nott'm Forest",
         "Sunderland", "Spurs", "West Ham", "Wolves"]
SHORT = ["ARS", "AVL", "BOU", "BRE", "BHA", "BUR", "CHE", "CRY", "EVE", "FUL", "LEE", "LIV", "MCI", "MUN", "NEW",
         "NFO", "SUN", "TOT", "WHU", "WOL"]
PLAYED, NEXT_GW, N_GW = 8, 9, 38
SQUAD_SHAPE = {1: 3, 2: 8, 3: 9, 4: 5}  # per club
PRICE = {1: (4.0, 6.0), 2: (4.0, 7.0), 3: (4.5, 13.0), 4: (4.5, 15.0)}
START = datetime(2026, 8, 15, 14, 0, tzinfo=UTC)


def _build(seed: int = 7):
    rng = random.Random(seed)
    strength = {c: rng.uniform(0.7, 1.3) for c in range(1, 21)}

    # Round-robin fixtures (circle method), mirrored for the second half.
    teams = list(range(1, 21))
    rounds = []
    for r in range(19):
        pairs = [(teams[i], teams[19 - i]) for i in range(10)]
        rounds.append([(h, a) if r % 2 == 0 else (a, h) for h, a in pairs])
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    rounds += [[(a, h) for h, a in rnd] for rnd in rounds]

    def diff(opp):  # FPL difficulty 2..5 from opponent strength
        return min(5, max(2, round(2 + (strength[opp] - 0.7) / 0.6 * 3)))

    fixtures, fid = [], 1
    for gw, rnd in enumerate(rounds, start=1):
        for h, a in rnd:
            finished = gw <= PLAYED
            hs, as_ = (rng.randint(0, 3), rng.randint(0, 3)) if finished else (None, None)
            fixtures.append({"id": fid, "event": gw, "team_h": h, "team_a": a, "finished": finished,
                             "started": finished, "kickoff_time": (START + timedelta(days=7 * (gw - 1))).isoformat().replace("+00:00", "Z"),
                             "team_h_difficulty": diff(a), "team_a_difficulty": diff(h),
                             "team_h_score": hs, "team_a_score": as_})
            fid += 1

    elements, histories, pid = [], {}, 1
    for club in range(1, 21):
        for pos, count in SQUAD_SHAPE.items():
            for k in range(count):
                lo, hi = PRICE[pos]
                quality = rng.random() ** 1.5
                price = round((lo + (hi - lo) * quality) * 2) / 2
                regular = k < {1: 1, 2: 5, 3: 5, 4: 2}[pos]
                hist = []
                for gw in range(1, PLAYED + 1):
                    fx = next(f for f in fixtures if f["event"] == gw and club in (f["team_h"], f["team_a"]))
                    home = fx["team_h"] == club
                    d = fx["team_h_difficulty"] if home else fx["team_a_difficulty"]
                    plays = rng.random() < (0.9 if regular else 0.25)
                    mins = 90 if plays and rng.random() < 0.85 else (rng.randint(1, 60) if plays else 0)
                    mean = (1 + 6 * quality) * strength[club] * (1.4 - 0.15 * d) if mins >= 60 else (1 if mins else 0)
                    pts = max(-1, round(rng.gauss(mean, 1.8))) if mins else 0
                    xg = round(max(0.0, rng.gauss(0.05 + 0.4 * quality * (pos >= 3), 0.1)), 2) if mins else 0.0
                    xa = round(max(0.0, rng.gauss(0.03 + 0.25 * quality * (pos >= 2), 0.08)), 2) if mins else 0.0
                    hist.append({"element": pid, "fixture": fx["id"], "round": gw, "was_home": home,
                                 "opponent_team": fx["team_a"] if home else fx["team_h"], "total_points": pts,
                                 "minutes": mins, "starts": int(mins >= 60), "goals_scored": int(xg > 0.5),
                                 "assists": int(xa > 0.4), "bonus": 3 if pts >= 10 else (1 if pts >= 7 else 0),
                                 "bps": pts * 3, "ict_index": f"{max(0.0, pts * 1.2):.1f}", "expected_goals": f"{xg:.2f}",
                                 "expected_assists": f"{xa:.2f}", "expected_goals_conceded": f"{d * 0.3:.2f}",
                                 "value": int(price * 10), "kickoff_time": fx["kickoff_time"]})
                histories[pid] = hist
                tot = sum(h["total_points"] for h in hist)
                apps = sum(1 for h in hist if h["minutes"])
                recent = hist[-4:]
                injured = rng.random() < 0.04
                doubt = not injured and rng.random() < 0.05
                elements.append({
                    "id": pid, "web_name": f"{SHORT[club - 1].title()}{pos}{k}", "first_name": "Player",
                    "second_name": f"{SHORT[club - 1]}-{pos}-{k}", "team": club, "element_type": pos,
                    "now_cost": int(price * 10), "cost_change_event": rng.choice([0, 0, 0, 1, -1]),
                    "cost_change_start": rng.choice([0, 1, 2, -1]),
                    "total_points": tot, "points_per_game": f"{tot / apps if apps else 0:.1f}",
                    "form": f"{sum(h['total_points'] for h in recent) / 4:.1f}",
                    "selected_by_percent": f"{min(70.0, 0.5 + 60 * quality ** 2 * rng.random()):.1f}",
                    "minutes": sum(h["minutes"] for h in hist), "goals_scored": sum(h["goals_scored"] for h in hist),
                    "assists": sum(h["assists"] for h in hist), "clean_sheets": rng.randint(0, 4) if pos <= 2 else 0,
                    "bonus": sum(h["bonus"] for h in hist), "bps": sum(h["bps"] for h in hist),
                    "ict_index": f"{sum(float(h['ict_index']) for h in hist):.1f}",
                    "expected_goals": f"{sum(float(h['expected_goals']) for h in hist):.2f}",
                    "expected_assists": f"{sum(float(h['expected_assists']) for h in hist):.2f}",
                    "influence": "0.0", "creativity": "0.0", "threat": "0.0",
                    "status": "i" if injured else ("d" if doubt else "a"),
                    "news": "Hamstring injury - expected back in 3 weeks" if injured else ("Knock - 50% chance of playing" if doubt else ""),
                    "news_added": (START + timedelta(days=50)).isoformat() if (injured or doubt) else None,
                    "chance_of_playing_next_round": 0 if injured else (50 if doubt else None),
                    "chance_of_playing_this_round": 0 if injured else (50 if doubt else None),
                    "transfers_in_event": rng.randint(0, 200_000), "transfers_out_event": rng.randint(0, 150_000),
                })
                pid += 1

    events = [{"id": gw, "name": f"Gameweek {gw}", "deadline_time": (START + timedelta(days=7 * (gw - 1), hours=-1, minutes=-30)).isoformat().replace("+00:00", "Z"),
               "finished": gw <= PLAYED, "is_current": gw == PLAYED, "is_next": gw == NEXT_GW,
               "average_entry_score": 50 if gw <= PLAYED else 0, "highest_score": 110 if gw <= PLAYED else None}
              for gw in range(1, N_GW + 1)]
    bootstrap = {
        "events": events, "elements": elements,
        "teams": [{"id": i, "name": CLUBS[i - 1], "short_name": SHORT[i - 1], "strength": round(strength[i] * 3)} for i in range(1, 21)],
        "element_types": [{"id": 1, "singular_name_short": "GKP", "plural_name_short": "GKP"},
                          {"id": 2, "singular_name_short": "DEF", "plural_name_short": "DEF"},
                          {"id": 3, "singular_name_short": "MID", "plural_name_short": "MID"},
                          {"id": 4, "singular_name_short": "FWD", "plural_name_short": "FWD"}],
    }
    return bootstrap, fixtures, histories


BOOTSTRAP, FIXTURES, HISTORIES = _build()
app = FastAPI(title="Mock FPL API")


@app.get("/api/bootstrap-static/")
def bootstrap():
    return BOOTSTRAP


@app.get("/api/fixtures/")
def fixtures():
    return FIXTURES


@app.get("/api/element-summary/{pid}/")
def element_summary(pid: int):
    if pid not in HISTORIES:
        raise HTTPException(404)
    club = next(e["team"] for e in BOOTSTRAP["elements"] if e["id"] == pid)
    upcoming = [{"event": f["event"], "is_home": f["team_h"] == club,
                 "difficulty": f["team_h_difficulty"] if f["team_h"] == club else f["team_a_difficulty"],
                 "kickoff_time": f["kickoff_time"]}
                for f in FIXTURES if not f["finished"] and club in (f["team_h"], f["team_a"])][:5]
    return {"history": HISTORIES[pid], "fixtures": upcoming, "history_past": []}


def _squad_ids() -> list[int]:
    """A legal 15: 2/5/5/3, ≤3 per club, cheapest-first so it fits £100m."""
    need, per_club, ids = {1: 2, 2: 5, 3: 5, 4: 3}, {}, []
    for e in sorted(BOOTSTRAP["elements"], key=lambda e: (e["element_type"], -float(e["form"]))):
        if need[e["element_type"]] and per_club.get(e["team"], 0) < 3 and e["status"] == "a":
            ids.append(e["id"])
            need[e["element_type"]] -= 1
            per_club[e["team"]] = per_club.get(e["team"], 0) + 1
    return ids


@app.get("/api/entry/{entry_id}/")
def entry(entry_id: int):
    if entry_id != 1:
        raise HTTPException(404)
    return {"id": 1, "name": "Demo XI", "player_first_name": "Demo", "player_last_name": "Manager",
            "summary_overall_points": 512, "summary_overall_rank": 123_456, "summary_event_points": 61,
            "last_deadline_bank": 15, "last_deadline_value": 1002}


@app.get("/api/entry/{entry_id}/event/{gw}/picks/")
def picks(entry_id: int, gw: int):
    if entry_id != 1:
        raise HTTPException(404)
    ids = _squad_ids()
    els = {e["id"]: e for e in BOOTSTRAP["elements"]}
    # XI: 1 GK, then 4-4-2 by order; bench: GK2 + remaining outfield
    gks = [i for i in ids if els[i]["element_type"] == 1]
    outfield = [i for i in ids if els[i]["element_type"] != 1]
    xi = [gks[0]] + [i for i in outfield if els[i]["element_type"] == 2][:4] + \
         [i for i in outfield if els[i]["element_type"] == 3][:4] + [i for i in outfield if els[i]["element_type"] == 4][:2]
    bench = [gks[1]] + [i for i in outfield if i not in xi]
    order = xi + bench
    return {"picks": [{"element": pid, "position": n, "multiplier": 2 if n == 9 else (1 if n <= 11 else 0),
                       "is_captain": n == 9, "is_vice_captain": n == 10} for n, pid in enumerate(order, start=1)],
            "entry_history": {"event": gw, "points": 61, "event_transfers": 0, "bank": 15}, "active_chip": None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    uvicorn.run(app, host="127.0.0.1", port=ap.parse_args().port, log_level="warning")
