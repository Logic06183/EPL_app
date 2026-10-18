"""
Train the expected-points model and backtest it on held-out seasons.

    python -m ml.train --data /path/to/vaastav-csvs

Data: https://github.com/vaastav/Fantasy-Premier-League (data/<season>/gws/merged_gw.csv
and data/<season>/teams.csv), saved as merged_<season>.csv / teams_<season>.csv.
Pass --download to fetch them into --data.

Writes app/ml/model.joblib (trained on every season) and app/ml/backtest.json
(walk-forward: each test season is predicted by a model trained only on
earlier seasons).
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from app.ml.features import (
    CORE_STATS, EXTRA_STATS, FEATURES, POSITIONS, add_position_code, attach_fixture_features,
    ownership_features, player_form, prior_season, team_form,
)

SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
PRIOR = {"2022-23": "2021-22", "2023-24": "2022-23", "2024-25": "2023-24", "2025-26": "2024-25"}
TEST_SEASONS = ["2024-25", "2025-26"]
RAW = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "ml"


def download(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for s in SEASONS + [PRIOR[SEASONS[0]]]:
        for remote, local in ((f"{s}/gws/merged_gw.csv", f"merged_{s}.csv"),
                              (f"{s}/teams.csv", f"teams_{s}.csv"),
                              (f"{s}/players_raw.csv", f"players_raw_{s}.csv")):
            urllib.request.urlretrieve(f"{RAW}/{remote}", data_dir / local)


def load_season(data_dir: Path, season: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (fixture-level rows, player_gw, fixtures) for one season."""
    raw = pd.read_csv(data_dir / f"merged_{season}.csv")
    teams = pd.read_csv(data_dir / f"teams_{season}.csv")
    raw = raw[raw["position"].isin(POSITIONS)].copy()   # drops 2024-25 assistant managers
    raw["team"] = raw["team"].map(dict(zip(teams["name"], teams["id"])))
    raw = raw.rename(columns={"GW": "gw", "opponent_team": "opponent"})
    raw["was_home"] = raw["was_home"].astype(bool).astype(int)
    if "starts" not in raw:
        raw["starts"] = (raw["minutes"] >= 60).astype(int)

    present_extra = [c for c in EXTRA_STATS if c in raw.columns]
    stats = CORE_STATS + present_extra
    raw[stats] = raw[stats].fillna(0)
    for c in ("selected", "transfers_balance"):
        if c not in raw:
            raw[c] = np.nan

    player_gw = (raw.groupby(["element", "gw"])
                 .agg(team=("team", "last"), position=("position", "last"), value=("value", "last"),
                      selected=("selected", "last"), transfers_balance=("transfers_balance", "last"),
                      n_fixtures=("fixture", "nunique"), **{c: (c, "sum") for c in stats})
                 .reset_index())
    for c in EXTRA_STATS:
        if c not in present_extra:
            player_gw[c] = np.nan   # stat not recorded that season (not zero)

    fx = raw.drop_duplicates("fixture")
    fixtures = pd.DataFrame({
        "gw": fx["gw"],
        "team_h": np.where(fx["was_home"] == 1, fx["team"], fx["opponent"]),
        "team_a": np.where(fx["was_home"] == 1, fx["opponent"], fx["team"]),
        "team_h_score": fx["team_h_score"],
        "team_a_score": fx["team_a_score"],
        "finished": True,
    })

    rows = raw[["element", "gw", "fixture", "team", "opponent", "was_home", "position",
                "value", "total_points", "minutes", "xP"]].copy()
    rows = rows.merge(player_form(player_gw), on=["element", "gw"], how="left")
    rows = rows.merge(ownership_features(player_gw), on=["element", "gw"], how="left")
    rows = attach_fixture_features(rows, team_form(fixtures, player_gw))
    codes = pd.read_csv(data_dir / f"players_raw_{season}.csv")[["id", "code"]]
    prior = prior_season(pd.read_csv(data_dir / f"players_raw_{PRIOR[season]}.csv"))
    rows = (rows.merge(codes.rename(columns={"id": "element"}), on="element", how="left")
            .merge(prior, on="code", how="left"))
    rows = add_position_code(rows)
    rows["season"] = season
    return rows, player_gw, fixtures


def make_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=100,
        l2_regularization=1.0, categorical_features=[FEATURES.index("position_code")],
        random_state=0,
    )


def _spearman(a: pd.Series, b: pd.Series) -> float:
    return float(a.rank().corr(b.rank()))


def evaluate(test: pd.DataFrame) -> dict:
    """
    Compare predictors on one held-out season, per gameweek, then averaged.
    Predictions are summed per player-gameweek (double gameweeks) first.
    """
    per_gw = (test.groupby(["gw", "element"])
              .agg(actual=("total_points", "sum"), model=("pred", "sum"), fpl_xp=("xP", "sum"),
                   season_avg=("pts_season", "first"), form=("pts_l6", "first"),
                   n=("fixture", "nunique"), mins_l6=("mins_l6", "first"))
              .reset_index())
    # Naive baselines are per-fixture rates; scale to the gw's fixture count
    per_gw["season_avg"] = per_gw["season_avg"].fillna(0) * per_gw["n"]
    per_gw["form"] = per_gw["form"].fillna(0) * per_gw["n"]

    # FPL's xP is missing for many 2025-26 gameweeks; only score it where present
    xp_ok = per_gw.groupby("gw")["fpl_xp"].transform(lambda s: (s != 0).mean() > 0.3)

    # Score the decision-relevant pool: players who've been getting minutes
    pool = per_gw[per_gw["mins_l6"].fillna(0) >= 30]

    out = {}
    for name in ("model", "season_avg", "form", "fpl_xp"):
        d = pool[xp_ok.loc[pool.index]] if name == "fpl_xp" else pool
        if d.empty:
            continue
        gws = d.groupby("gw")
        top1 = gws.apply(lambda g: g.nlargest(1, name)["actual"].mean(), include_groups=False)
        top11 = gws.apply(lambda g: g.nlargest(11, name)["actual"].mean(), include_groups=False)
        out[name] = {
            "gameweeks": int(d["gw"].nunique()),
            "mae": round(float((d[name] - d["actual"]).abs().mean()), 3),
            "spearman": round(float(gws.apply(lambda g: _spearman(g[name], g["actual"]), include_groups=False).mean()), 3),
            "captain_pts": round(float(top1.mean()), 2),
            "top11_pts": round(float(top11.mean()), 2),
        }
    # Same-gameweek comparison against FPL's xP (only where it exists)
    d = pool[xp_ok.loc[pool.index]]
    if not d.empty:
        gws = d.groupby("gw")
        out["model_on_fpl_xp_gws"] = {
            "gameweeks": int(d["gw"].nunique()),
            "mae": round(float((d["model"] - d["actual"]).abs().mean()), 3),
            "spearman": round(float(gws.apply(lambda g: _spearman(g["model"], g["actual"]), include_groups=False).mean()), 3),
            "captain_pts": round(float(gws.apply(lambda g: g.nlargest(1, "model")["actual"].mean(), include_groups=False).mean()), 2),
            "top11_pts": round(float(gws.apply(lambda g: g.nlargest(11, "model")["actual"].mean(), include_groups=False).mean()), 2),
        }
    out["model_vs_season_avg"] = paired_differences(pool)
    return out


def paired_differences(pool: pd.DataFrame, n_boot: int = 5000, seed: int = 0) -> dict:
    """
    Per-gameweek model minus season-average difference for each pick metric,
    with a bootstrap 95% interval over gameweeks. If the interval spans zero,
    the backtest can't tell the two apart on that metric.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for metric, k in (("captain_pts", 1), ("top3_pts", 3), ("top11_pts", 11)):
        per_gw = pool.groupby("gw").apply(
            lambda g: g.nlargest(k, "model")["actual"].mean() - g.nlargest(k, "season_avg")["actual"].mean(),
            include_groups=False,
        ).to_numpy()
        boots = [rng.choice(per_gw, len(per_gw)).mean() for _ in range(n_boot)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[metric] = {"diff": round(float(per_gw.mean()), 2), "ci95": [round(float(lo), 2), round(float(hi), 2)],
                       "significant": bool(lo > 0 or hi < 0)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()

    if args.download:
        download(args.data)

    seasons = {s: load_season(args.data, s)[0] for s in SEASONS}

    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "features": FEATURES, "seasons": {}}
    for test_season in TEST_SEASONS:
        train = pd.concat([seasons[s] for s in SEASONS if s < test_season])
        model = make_model().fit(train[FEATURES], train["total_points"])
        test = seasons[test_season].copy()
        test["pred"] = model.predict(test[FEATURES])
        report["seasons"][test_season] = {
            "trained_on": [s for s in SEASONS if s < test_season],
            "metrics": evaluate(test),
        }
        print(test_season, json.dumps(report["seasons"][test_season]["metrics"], indent=1))

    full = pd.concat(seasons.values())
    model = make_model().fit(full[FEATURES], full["total_points"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "trained_on": SEASONS}, OUT_DIR / "model.joblib")
    # Priors for the season after the last one trained on (i.e. the live season)
    prior_season(pd.read_csv(args.data / f"players_raw_{SEASONS[-1]}.csv")).to_csv(
        OUT_DIR / "prior_season.csv", index=False)
    (OUT_DIR / "backtest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("wrote", OUT_DIR / "model.joblib", OUT_DIR / "backtest.json")
    print(scorecard(report))


# The bar from GOAL.md ("Is it good at predictions?"), checked on every test season.
TARGETS = {
    "spearman": ("≥", 0.45),
    "mae": ("≤", 1.85),
}


def scorecard(report: dict) -> str:
    """One-screen pass/fail against GOAL.md for each held-out season."""
    lines = ["", "GOAL.md scorecard"]
    for season, body in report["seasons"].items():
        m, base, sig = body["metrics"]["model"], body["metrics"]["season_avg"], body["metrics"]["model_vs_season_avg"]
        checks = [
            ("spearman ≥ 0.45", m["spearman"] >= TARGETS["spearman"][1], f"{m['spearman']:.3f}"),
            ("mae ≤ 1.85", m["mae"] <= TARGETS["mae"][1], f"{m['mae']:.3f}"),
            ("captain beats season avg (CI > 0)", sig["captain_pts"]["significant"] and sig["captain_pts"]["diff"] > 0,
             f"{sig['captain_pts']['diff']:+.2f} CI {sig['captain_pts']['ci95']}"),
            ("top-11 +0.5 over season avg, significant", sig["top11_pts"]["significant"] and sig["top11_pts"]["diff"] >= 0.5,
             f"{m['top11_pts']:.2f} vs {base['top11_pts']:.2f} ({sig['top11_pts']['diff']:+.2f})"),
        ]
        lines.append(f"  {season}")
        lines += [f"    {'PASS' if ok else 'FAIL'}  {name}  — {detail}" for name, ok, detail in checks]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
