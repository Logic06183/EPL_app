"""
Expected points (xP) for upcoming gameweeks, from the trained model in
app/ml/model.joblib (see ml/train.py and app/ml/backtest.json).

Rebuilds this season's per-gameweek history from the FPL API (fixtures +
event/{gw}/live), computes the same features used in training, and predicts
the next few gameweeks. Predictions are scaled by FPL's chance of playing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from . import track_record
from ..auth.firebase_auth import get_db
from ..ml.features import (
    POSITIONS, add_position_code, attach_fixture_features, fixture_rows, form_as_of, team_form,
)

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent.parent / "ml"
HORIZON = 3
REFRESH_SECONDS = 3600
RETRY_SECONDS = 300

_STATS = ["minutes", "starts", "total_points", "goals_scored", "assists",
          "expected_goals", "expected_assists", "bps"]


def fixtures_frame(fixtures: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = [f for f in fixtures if f.get("event")]
    return pd.DataFrame({
        "gw": [f["event"] for f in rows],
        "team_h": [f["team_h"] for f in rows],
        "team_a": [f["team_a"] for f in rows],
        "team_h_score": [f.get("team_h_score") for f in rows],
        "team_a_score": [f.get("team_a_score") for f in rows],
        "finished": [bool(f.get("finished")) for f in rows],
    })


def player_gw_frame(
    elements: List[Dict[str, Any]], live_by_gw: Dict[int, Dict[str, Any]], fixtures: pd.DataFrame,
) -> pd.DataFrame:
    """One row per (element, gw) where the player's current team had a finished fixture."""
    team_of = {e["id"]: e["team"] for e in elements}
    pos_of = {e["id"]: POSITIONS[e["element_type"] - 1] for e in elements if 1 <= e["element_type"] <= 4}
    done = fixtures[fixtures["finished"]]
    nfix = pd.concat([done[["team_h", "gw"]].rename(columns={"team_h": "team"}),
                      done[["team_a", "gw"]].rename(columns={"team_a": "team"})]).value_counts()
    nfix = {(int(t), int(g)): int(n) for (t, g), n in nfix.items()}

    out = []
    for gw, live in live_by_gw.items():
        for row in live.get("elements", []):
            el = row["id"]
            team = team_of.get(el)
            if team is None or el not in pos_of or (team, gw) not in nfix:
                continue
            st = row.get("stats", {})
            rec = {"element": el, "gw": gw, "team": team, "position": pos_of[el],
                   "n_fixtures": nfix[(team, gw)]}
            for c in _STATS:
                rec[c] = float(st.get(c) or 0)
            out.append(rec)
    return pd.DataFrame(out, columns=["element", "gw", "team", "position", "n_fixtures"] + _STATS)


def predict_gameweeks(
    model_bundle: Dict[str, Any],
    elements: List[Dict[str, Any]],
    player_gw: pd.DataFrame,
    fixtures: pd.DataFrame,
    next_gw: int,
    prior: Optional[pd.DataFrame] = None,
    horizon: int = HORIZON,
) -> Dict[int, Dict[int, float]]:
    """
    Returns {element_id: {gw: xP}} for gws next_gw .. next_gw+horizon-1.
    All features are as of the start of next_gw; later gws only change the
    fixture (opponent, home/away, doubles and blanks).
    """
    model, features = model_bundle["model"], model_bundle["features"]

    els = pd.DataFrame({
        "element": [e["id"] for e in elements],
        "code": [e.get("code") for e in elements],
        "team": [e["team"] for e in elements],
        "position": [POSITIONS[e["element_type"] - 1] if 1 <= e["element_type"] <= 4 else None
                     for e in elements],
        "value": [e.get("now_cost", 0) for e in elements],
    }).dropna(subset=["position"])

    form = form_as_of(player_gw, next_gw) if not player_gw.empty else pd.DataFrame(columns=["element"])
    tform = team_form(fixtures, player_gw if not player_gw.empty else None)
    tform_now = tform[tform["gw"] == next_gw].drop(columns=["gw"])

    fx = fixture_rows(fixtures)
    target_gws = list(range(next_gw, next_gw + horizon))
    fx = fx[fx["fixture_gw"].isin(target_gws)]

    frame = els.merge(fx, on="team", how="inner").merge(form, on="element", how="left")
    frame["gw"] = next_gw  # team form as of the start of next_gw
    frame = attach_fixture_features(frame, tform_now.assign(gw=next_gw))
    if prior is not None:
        frame = frame.merge(prior, on="code", how="left")
    frame = add_position_code(frame)
    for col in features:
        if col not in frame:
            frame[col] = np.nan
    # Players with no history this season: training sees 0 games, not unknown
    frame["games_season"] = frame["games_season"].fillna(0)

    out: Dict[int, Dict[int, float]] = {int(e): {gw: 0.0 for gw in target_gws} for e in els["element"]}
    if frame.empty:
        return out
    frame["pred"] = model.predict(frame[features].astype(float))
    per_gw = frame.groupby(["element", "fixture_gw"])["pred"].sum()
    for (el, gw), v in per_gw.items():
        out[int(el)][int(gw)] = max(0.0, float(v))
    return out


def availability(element: Dict[str, Any]) -> float:
    """FPL's chance of playing next round as a 0-1 multiplier."""
    if element.get("status") == "u":   # left the club / unavailable for the season
        return 0.0
    chance = element.get("chance_of_playing_next_round")
    return 1.0 if chance is None else max(0.0, min(1.0, chance / 100))


class XPService:
    def __init__(self) -> None:
        self._bundle: Optional[Dict[str, Any]] = None
        self._prior: Optional[pd.DataFrame] = None
        self._backtest: Optional[Dict[str, Any]] = None
        self.xp: Dict[int, Dict[int, float]] = {}
        # (team, gw) -> number of fixtures, for double/blank gameweek detection
        self.fixture_counts: Dict[tuple, int] = {}
        self.next_gw: Optional[int] = None
        self.updated_at: Optional[datetime] = None
        self._failed_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    def _load(self) -> None:
        if self._bundle is None:
            self._bundle = joblib.load(ML_DIR / "model.joblib")
            prior_path = ML_DIR / "prior_season.csv"
            if prior_path.exists():
                self._prior = pd.read_csv(prior_path)
            bt = ML_DIR / "backtest.json"
            if bt.exists():
                self._backtest = json.loads(bt.read_text())

    @property
    def ready(self) -> bool:
        return bool(self.xp)

    @property
    def backtest(self) -> Optional[Dict[str, Any]]:
        self._load()
        return self._backtest

    def _stale(self) -> bool:
        now = datetime.now(timezone.utc)
        if self._failed_at and (now - self._failed_at).total_seconds() < RETRY_SECONDS:
            return False
        return self.updated_at is None or (now - self.updated_at).total_seconds() > REFRESH_SECONDS

    async def ensure_fresh(self, data_service) -> None:
        if not self._stale():
            return
        async with self._lock:
            if self._stale():
                await self.refresh(data_service)

    async def refresh(self, data_service) -> None:
        """Fetch this season's history and recompute xP. Leaves old values on failure."""
        try:
            self._load()
            bootstrap = await data_service.get_bootstrap_data()
            events = bootstrap.get("events", [])
            nxt = next((e for e in events if e.get("is_next")), None)
            if nxt is None:
                # Season over: nothing to predict. Mark fresh so requests
                # don't re-run this every time.
                logger.info("xP: no upcoming gameweek (season over?)")
                self.updated_at = datetime.now(timezone.utc)
                return
            next_gw = int(nxt["id"])
            fixtures = fixtures_frame(await data_service.get_all_fixtures())

            finished = [e["id"] for e in events if e["id"] < next_gw and e.get("finished")]
            sem = asyncio.Semaphore(8)

            async def fetch(gw: int):
                async with sem:
                    return gw, await data_service.get_event_live(gw, finished=True)

            live_by_gw: Dict[int, Dict[str, Any]] = dict(await asyncio.gather(*(fetch(gw) for gw in finished)))

            elements = bootstrap.get("elements", [])
            player_gw = player_gw_frame(elements, live_by_gw, fixtures)
            raw = await asyncio.to_thread(
                predict_gameweeks, self._bundle, elements, player_gw, fixtures, next_gw, self._prior,
            )
            avail = {e["id"]: availability(e) for e in elements}
            # Chance of playing applies to the next gw only; later gws assume fit
            for el, by_gw in raw.items():
                by_gw[next_gw] = by_gw.get(next_gw, 0.0) * avail.get(el, 1.0)
            self.xp = raw
            self.next_gw = next_gw
            counts = pd.concat([fixtures[["team_h", "gw"]].rename(columns={"team_h": "team"}),
                                fixtures[["team_a", "gw"]].rename(columns={"team_a": "team"})]).value_counts()
            self.fixture_counts = {(int(t), int(g)): int(n) for (t, g), n in counts.items()}
            self.updated_at = datetime.now(timezone.utc)
            self._failed_at = None
            logger.info(f"xP refreshed for GW{next_gw}: {len(raw)} players, {len(live_by_gw)} GWs of history")
            await self._record(events, nxt, elements, player_gw, fixtures, live_by_gw)
        except Exception as e:
            self._failed_at = datetime.now(timezone.utc)
            logger.error(f"xP refresh failed: {e}")

    async def _record(self, events, nxt, elements, player_gw, fixtures, live_by_gw) -> None:
        """Snapshot this gameweek's predictions and score finished ones (best effort)."""
        try:
            db = get_db()
            if db is None:
                return
            next_gw = int(nxt["id"])
            form = (form_as_of(player_gw, next_gw).set_index("element")
                    if not player_gw.empty else pd.DataFrame(columns=["pts_season", "mins_l6"]))
            team_fix = fixtures[fixtures["gw"] == next_gw]
            nfix = pd.concat([team_fix["team_h"], team_fix["team_a"]]).value_counts().to_dict()
            team_of = {e["id"]: e["team"] for e in elements}
            baseline = {
                el: float(form["pts_season"].get(el, 0) or 0) * nfix.get(team_of.get(el), 0)
                for el in team_of if el in form.index
            }
            pool = [int(el) for el, m in form["mins_l6"].items() if pd.notna(m) and m >= 30]
            names = {e["id"]: e.get("web_name", "") for e in elements}
            snap = track_record.build_snapshot(
                next_gw, {el: v.get(next_gw, 0.0) for el, v in self.xp.items()},
                baseline, pool, names, nxt["deadline_time"],
            )
            season = track_record.season_label(events)
            actual = {
                gw: {r["id"]: float(r.get("stats", {}).get("total_points", 0)) for r in live.get("elements", [])}
                for gw, live in live_by_gw.items()
            }
            await asyncio.to_thread(track_record.save_snapshot, db, season, snap)
            n = await asyncio.to_thread(track_record.score_pending, db, season, sorted(actual), actual)
            if n:
                logger.info(f"Track record: scored {n} gameweek(s)")
        except Exception as e:
            logger.warning(f"Track record update failed: {e}")

    def next_xp(self, element_id: int) -> Optional[float]:
        by_gw = self.xp.get(element_id)
        if by_gw is None or self.next_gw is None:
            return None
        return by_gw.get(self.next_gw, 0.0)

    def horizon_xp(self, element_id: int) -> List[float]:
        by_gw = self.xp.get(element_id, {})
        return [round(by_gw[gw], 2) for gw in sorted(by_gw)]


@lru_cache()
def get_xp_service() -> XPService:
    return XPService()
