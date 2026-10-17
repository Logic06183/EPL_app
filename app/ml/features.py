"""
Feature pipeline for next-gameweek expected points.

Shared by offline training (historical seasons) and live serving (current
season from the FPL API), so a backtest measures exactly what production runs.

Inputs are two tidy tables:

player_gw — one row per (element, gw) the player's team had a fixture,
    aggregated over double gameweeks:
    element, gw, team, position, value, minutes, starts, total_points,
    goals_scored, assists, expected_goals, expected_assists, bps, n_fixtures

fixtures — one row per match:
    gw, team_h, team_a, team_h_score, team_a_score, finished

Every feature for gameweek t uses data from gameweeks < t only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

POSITIONS = ["GK", "DEF", "MID", "FWD"]

FEATURES = [
    "position_code",
    "value",
    "was_home",
    "pts_l3",
    "pts_l6",
    "pts_season",
    "mins_l3",
    "mins_l6",
    "starts_l6",
    "xgi90_l6",
    "xgi90_season",
    "bps_l6",
    "games_season",
    "team_scored_l6",
    "team_conceded_l6",
    "opp_scored_l6",
    "opp_conceded_l6",
    "team_xg_for_l6",
    "team_xg_against_l6",
    "opp_xg_for_l6",
    "opp_xg_against_l6",
    "prev_pts90",
    "prev_mins_pg",
    "prev_xgi90",
]

PRIOR_FEATURES = ["prev_pts90", "prev_mins_pg", "prev_xgi90"]


def _shifted_rolling(g: pd.core.groupby.SeriesGroupBy, window: int | None) -> pd.Series:
    """Mean over the previous `window` rows (or all previous rows), excluding the current one."""
    if window is None:
        return g.transform(lambda s: s.shift(1).expanding().mean())
    return g.transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())


def _shifted_sum(g: pd.core.groupby.SeriesGroupBy, window: int | None) -> pd.Series:
    if window is None:
        return g.transform(lambda s: s.shift(1).expanding().sum())
    return g.transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())


def player_form(player_gw: pd.DataFrame) -> pd.DataFrame:
    """
    Per (element, gw) form features computed from strictly earlier gameweeks.
    Rows are the gameweeks in player_gw; use `form_as_of` for a future gw.
    """
    df = player_gw.sort_values(["element", "gw"]).copy()
    # Per-fixture rates so double gameweeks don't look like hot streaks
    nf = df["n_fixtures"].clip(lower=1)
    df["_pts"] = df["total_points"] / nf
    df["_mins"] = df["minutes"] / nf
    df["_starts"] = df["starts"] / nf
    df["_bps"] = df["bps"] / nf
    df["_xgi"] = df["expected_goals"] + df["expected_assists"]

    g = df.groupby("element")
    out = df[["element", "gw"]].copy()
    out["pts_l3"] = _shifted_rolling(g["_pts"], 3)
    out["pts_l6"] = _shifted_rolling(g["_pts"], 6)
    out["pts_season"] = _shifted_rolling(g["_pts"], None)
    out["mins_l3"] = _shifted_rolling(g["_mins"], 3)
    out["mins_l6"] = _shifted_rolling(g["_mins"], 6)
    out["starts_l6"] = _shifted_rolling(g["_starts"], 6)
    out["bps_l6"] = _shifted_rolling(g["_bps"], 6)
    out["games_season"] = g["n_fixtures"].transform(lambda s: s.shift(1).fillna(0).cumsum())

    xgi6 = _shifted_sum(g["_xgi"], 6)
    min6 = _shifted_sum(g["minutes"], 6)
    xgis = _shifted_sum(g["_xgi"], None)
    mins = _shifted_sum(g["minutes"], None)
    out["xgi90_l6"] = np.where(min6 > 0, 90 * xgi6 / min6.where(min6 > 0, 1), np.nan)
    out["xgi90_season"] = np.where(mins > 0, 90 * xgis / mins.where(mins > 0, 1), np.nan)
    return out


def form_as_of(player_gw: pd.DataFrame, gw: int) -> pd.DataFrame:
    """Form features for every player as of the start of `gw` (uses gws < gw)."""
    hist = player_gw[player_gw["gw"] < gw]
    if hist.empty:
        return pd.DataFrame(columns=["element"] + [c for c in FEATURES if c.endswith(("_l3", "_l6", "_season"))])
    # Append a placeholder row at `gw` per player so the shifted features land on it
    last = hist.sort_values("gw").groupby("element").tail(1).copy()
    placeholder = last.assign(gw=gw, n_fixtures=1)
    for col in ("minutes", "starts", "total_points", "goals_scored", "assists",
                "expected_goals", "expected_assists", "bps"):
        placeholder[col] = 0
    form = player_form(pd.concat([hist, placeholder], ignore_index=True))
    return form[form["gw"] == gw].drop(columns=["gw"])


def team_form(fixtures: pd.DataFrame, player_gw: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Per (team, gw) form from finished matches in earlier gameweeks, averaged
    per match over the last 6: goals scored/conceded and, when player_gw is
    given, expected goals for/against (summed from players' xG). Defined for
    every gw from 1 to max(gw)+1.
    """
    done = fixtures[fixtures["finished"].astype(bool)].copy()

    if player_gw is not None:
        nfix = pd.concat([
            done[["gw", "team_h"]].rename(columns={"team_h": "team"}),
            done[["gw", "team_a"]].rename(columns={"team_a": "team"}),
        ]).value_counts().rename("nfix").reset_index()
        xg = (player_gw.groupby(["team", "gw"])["expected_goals"].sum().reset_index()
              .merge(nfix, on=["team", "gw"], how="inner"))
        xg["xg"] = xg["expected_goals"] / xg["nfix"]
        xg = xg.set_index(["team", "gw"])["xg"]
        done["xg_h"] = [xg.get((t, g), np.nan) for t, g in zip(done["team_h"], done["gw"])]
        done["xg_a"] = [xg.get((t, g), np.nan) for t, g in zip(done["team_a"], done["gw"])]
    else:
        done["xg_h"] = np.nan
        done["xg_a"] = np.nan

    rows = pd.concat([
        pd.DataFrame({"team": done["team_h"], "gw": done["gw"],
                      "scored": done["team_h_score"], "conceded": done["team_a_score"],
                      "xg_for": done["xg_h"], "xg_against": done["xg_a"]}),
        pd.DataFrame({"team": done["team_a"], "gw": done["gw"],
                      "scored": done["team_a_score"], "conceded": done["team_h_score"],
                      "xg_for": done["xg_a"], "xg_against": done["xg_h"]}),
    ]).sort_values(["team", "gw"])

    teams = pd.unique(pd.concat([fixtures["team_h"], fixtures["team_a"]]))
    max_gw = int(fixtures["gw"].max()) + 1
    out = []
    for team in teams:
        t = rows[rows["team"] == team]
        for gw in range(1, max_gw + 1):
            prev = t[t["gw"] < gw].tail(6)
            out.append({
                "team": team, "gw": gw,
                "scored_l6": prev["scored"].mean() if len(prev) else np.nan,
                "conceded_l6": prev["conceded"].mean() if len(prev) else np.nan,
                "xg_for_l6": prev["xg_for"].mean() if len(prev) else np.nan,
                "xg_against_l6": prev["xg_against"].mean() if len(prev) else np.nan,
            })
    return pd.DataFrame(out)


def fixture_rows(fixtures: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, fixture) with home/away and opponent."""
    home = pd.DataFrame({"fixture_gw": fixtures["gw"], "team": fixtures["team_h"],
                         "opponent": fixtures["team_a"], "was_home": 1})
    away = pd.DataFrame({"fixture_gw": fixtures["gw"], "team": fixtures["team_a"],
                         "opponent": fixtures["team_h"], "was_home": 0})
    return pd.concat([home, away], ignore_index=True)


def attach_fixture_features(frame: pd.DataFrame, tform: pd.DataFrame) -> pd.DataFrame:
    """frame needs team, opponent, gw. Adds own and opponent team form."""
    own = tform.rename(columns={"scored_l6": "team_scored_l6", "conceded_l6": "team_conceded_l6",
                                "xg_for_l6": "team_xg_for_l6", "xg_against_l6": "team_xg_against_l6"})
    opp = tform.rename(columns={"team": "opponent", "scored_l6": "opp_scored_l6",
                                "conceded_l6": "opp_conceded_l6",
                                "xg_for_l6": "opp_xg_for_l6", "xg_against_l6": "opp_xg_against_l6"})
    frame = frame.merge(own, on=["team", "gw"], how="left")
    frame = frame.merge(opp, on=["opponent", "gw"], how="left")
    return frame


def prior_season(players_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Previous-season priors keyed by FPL's stable player `code` (element ids
    change every season). Input is a season's end-of-season players table
    (vaastav players_raw.csv, or the FPL bootstrap `elements` at season end).
    """
    mins = players_raw["minutes"].astype(float)
    played = mins >= 270  # ~3 full games, else the rate is noise
    out = pd.DataFrame({"code": players_raw["code"].astype(int)})
    out["prev_pts90"] = np.where(played, 90 * players_raw["total_points"] / mins.where(played, 1), np.nan)
    out["prev_mins_pg"] = mins / 38
    xgi = players_raw.get("expected_goal_involvements")
    out["prev_xgi90"] = (np.where(played, 90 * xgi.astype(float) / mins.where(played, 1), np.nan)
                         if xgi is not None else np.nan)
    return out


def add_position_code(frame: pd.DataFrame) -> pd.DataFrame:
    frame["position_code"] = frame["position"].map({p: i for i, p in enumerate(POSITIONS)})
    return frame
