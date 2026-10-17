"""
Squad and transfer optimiser: an integer programme over the model's
per-gameweek expected points.

Decides the 15-man squad, and for each gameweek in the horizon the starting
XI and captain, subject to FPL's rules (budget, 2/5/5/3, max 3 per club,
valid formation). With a current squad it also charges -4 per transfer beyond
the free ones, so "hold" is always on the table.

Prices: FPL's public API doesn't expose a manager's selling prices, so
current players are valued at their current price (selling price can be up
to half the rise lower). Plans can be a little optimistic on budget as a
result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

SQUAD_SHAPE = {1: 2, 2: 5, 3: 5, 4: 3}            # element_type -> squad count
XI_MIN = {1: 1, 2: 3, 3: 2, 4: 1}
XI_MAX = {1: 1, 2: 5, 3: 5, 4: 3}
MAX_PER_CLUB = 3
HIT_COST = 4.0
BENCH_WEIGHT = 0.1      # bench points are worth a little (auto-subs)


@dataclass
class Candidate:
    id: int
    position: int       # element_type 1-4
    team: int
    price: float        # £m
    xp: Sequence[float]  # expected points per gameweek in the horizon


@dataclass
class Plan:
    squad: List[int]
    transfers_in: List[int]
    transfers_out: List[int]
    hits: int
    lineups: List[List[int]]        # starting XI per gameweek
    captains: List[int]
    expected_points: float          # XI + captain over the horizon, after hits
    cost: float
    status: str = "optimal"
    per_gw_points: List[float] = field(default_factory=list)


def estimate_free_transfers(history: dict) -> int:
    """
    Free transfers available for the next deadline, replayed from a manager's
    /entry/{id}/history/: 1 per gameweek from GW2, banked up to 5; a Wildcard
    or Free Hit doesn't use banked transfers. Ignores one-off top-ups FPL
    occasionally grants, so the UI lets the user override it.
    """
    chips = {c.get("event"): c.get("name") for c in history.get("chips", [])}
    ft = 0
    for gw in sorted(history.get("current", []), key=lambda e: e["event"]):
        event = gw["event"]
        if event == 1:
            ft = 1
            continue
        if chips.get(event) not in ("wildcard", "freehit"):
            ft = max(0, ft - int(gw.get("event_transfers", 0)))
        ft = min(5, ft + 1)
    return max(1, ft) if history.get("current") else 1


def candidates_from_elements(elements: List[dict], prediction_service) -> List[Candidate]:
    """Build optimiser candidates from FPL bootstrap elements and the xP model."""
    out = []
    for e in elements:
        if e.get("element_type") not in SQUAD_SHAPE or e.get("status") == "u" or not e.get("now_cost"):
            continue
        xp = prediction_service.horizon(e["id"])
        if not xp:
            # Model not ready: flat form-based estimate for each gameweek
            xp = [prediction_service.predict(e, "basic")] * 3
        out.append(Candidate(e["id"], e["element_type"], e["team"], e["now_cost"] / 10, xp))
    return out


def _shortlist(cands: List[Candidate], keep_ids: set, top_n: int = 220, cheap_per_pos: int = 8) -> List[Candidate]:
    """Best players by horizon xP, plus the current squad and cheap bench options."""
    by_total = sorted(cands, key=lambda c: sum(c.xp), reverse=True)
    chosen = {c.id for c in by_total[:top_n]} | set(keep_ids)
    for pos in SQUAD_SHAPE:
        cheap = sorted((c for c in cands if c.position == pos), key=lambda c: (c.price, -sum(c.xp)))
        chosen |= {c.id for c in cheap[:cheap_per_pos]}
    return [c for c in cands if c.id in chosen]


def optimise(
    cands: List[Candidate],
    budget: float,
    current: Optional[Sequence[int]] = None,
    free_transfers: int = 1,
    max_transfers: Optional[int] = None,
    hit_cost: float = HIT_COST,
    bench_weight: float = BENCH_WEIGHT,
    time_limit: float = 10.0,
) -> Plan:
    """
    budget: total spend allowed (for a current squad, its value plus the bank).
    current: ids of the 15 players owned now; None builds from scratch.
    """
    current_set = set(current or [])
    cands = _shortlist(cands, current_set)
    n, horizon = len(cands), len(cands[0].xp) if cands else 0
    if n == 0 or horizon == 0:
        raise ValueError("No candidates to optimise over")
    building = not current_set
    if max_transfers is None:
        max_transfers = 15 if building else 3

    # Variable layout: x[n] | s[n*h] | c[n*h] | hits(1)
    nx, ns = n, n * horizon
    X, S, C, H = 0, nx, nx + ns, nx + 2 * ns
    nvar = H + 1

    def s_idx(i, g):
        return S + g * n + i

    def c_idx(i, g):
        return C + g * n + i

    xp = np.array([list(c.xp) for c in cands], dtype=float)
    obj = np.zeros(nvar)
    for g in range(horizon):
        for i in range(n):
            # starter gets xp, captain doubles it, bench gets a fraction
            obj[s_idx(i, g)] -= xp[i, g] * (1 - bench_weight)
            obj[c_idx(i, g)] -= xp[i, g]
            obj[X + i] -= xp[i, g] * bench_weight
    obj[H] = 0.0 if building else hit_cost

    rows, lo, hi = [], [], []

    def add(coefs: Dict[int, float], lb: float, ub: float):
        rows.append(coefs)
        lo.append(lb)
        hi.append(ub)

    # Squad shape and budget
    add({X + i: 1 for i in range(n)}, 15, 15)
    for pos, k in SQUAD_SHAPE.items():
        add({X + i: 1 for i, c in enumerate(cands) if c.position == pos}, k, k)
    add({X + i: c.price for i, c in enumerate(cands)}, 0, budget + 1e-6)
    for team in {c.team for c in cands}:
        add({X + i: 1 for i, c in enumerate(cands) if c.team == team}, 0, MAX_PER_CLUB)

    # Transfers: number of new players, hits beyond free transfers
    if not building:
        new = {X + i: 1 for i, c in enumerate(cands) if c.id not in current_set}
        add(new, 0, max_transfers)
        add({**new, H: -1}, -np.inf, free_transfers)

    # Lineup and captain per gameweek
    for g in range(horizon):
        add({s_idx(i, g): 1 for i in range(n)}, 11, 11)
        for pos in SQUAD_SHAPE:
            add({s_idx(i, g): 1 for i, c in enumerate(cands) if c.position == pos}, XI_MIN[pos], XI_MAX[pos])
        add({c_idx(i, g): 1 for i in range(n)}, 1, 1)
        for i in range(n):
            add({s_idx(i, g): 1, X + i: -1}, -np.inf, 0)
            add({c_idx(i, g): 1, s_idx(i, g): -1}, -np.inf, 0)

    A = lil_matrix((len(rows), nvar))
    for r, coefs in enumerate(rows):
        for j, v in coefs.items():
            A[r, j] = v

    ub = np.ones(nvar)
    ub[H] = 15
    res = milp(
        c=obj,
        constraints=LinearConstraint(A.tocsr(), np.array(lo), np.array(hi)),
        integrality=np.ones(nvar),
        bounds=Bounds(np.zeros(nvar), ub),
        options={"time_limit": time_limit, "mip_rel_gap": 1e-4},
    )
    if res.x is None:
        raise ValueError(f"No feasible plan ({res.message})")

    sol = np.round(res.x).astype(int)
    squad = [cands[i].id for i in range(n) if sol[X + i]]
    lineups = [[cands[i].id for i in range(n) if sol[s_idx(i, g)]] for g in range(horizon)]
    captains = [next(cands[i].id for i in range(n) if sol[c_idx(i, g)]) for g in range(horizon)]
    per_gw = [
        float(sum(xp[i, g] for i in range(n) if sol[s_idx(i, g)]) +
              sum(xp[i, g] for i in range(n) if sol[c_idx(i, g)]))
        for g in range(horizon)
    ]
    hits = 0 if building else int(sol[H])
    return Plan(
        squad=squad,
        transfers_in=[] if building else [p for p in squad if p not in current_set],
        transfers_out=[] if building else [p for p in current_set if p not in set(squad)],
        hits=hits,
        lineups=lineups,
        captains=captains,
        expected_points=round(sum(per_gw) - hits * hit_cost, 2),
        cost=round(sum(cands[i].price for i in range(n) if sol[X + i]), 1),
        status="optimal" if res.status == 0 else "time_limit",
        per_gw_points=[round(v, 2) for v in per_gw],
    )


# ── Chips ────────────────────────────────────────────────────────────────────

CHIPS = ("wildcard", "freehit", "bboost", "3xc")
CHIP_LABELS = {"wildcard": "Wildcard", "freehit": "Free Hit", "bboost": "Bench Boost", "3xc": "Triple Captain"}
WILDCARD_GAIN = 15.0      # xP over the horizon a rebuild must add over the best normal plan
BB_MIN_DOUBLES = 3        # squad players with two fixtures in the gw
FH_MIN_BLANKS = 4         # starters with no fixture in the gw


def chips_available(history: dict, next_gw: int) -> List[str]:
    """
    Chips not yet used in the current half of the season. Since 2025-26 each
    chip can be played once in GW1-19 and once in GW20-38.
    """
    half = (1, 19) if next_gw <= 19 else (20, 38)
    used = {c.get("name") for c in history.get("chips", []) if half[0] <= c.get("event", 0) <= half[1]}
    return [c for c in CHIPS if c not in used]


def chip_advice(
    plan: Plan,
    hold: Plan,
    wildcard_points: Optional[float],
    gws: List[int],
    team_of: Dict[int, int],
    fixture_counts: Dict[tuple, int],
    xp_of: Dict[int, Sequence[float]],
    available: List[str],
) -> List[dict]:
    """
    One entry per available chip: the best gameweek in the horizon, its
    expected gain, and whether the signal says play it now. Rules are simple
    and stated in each reason, so users can disagree with them.
    """
    def n_fix(pid: int, g: int) -> int:
        return fixture_counts.get((team_of.get(pid), gws[g]), 0)

    out = []
    for chip in available:
        if chip == "3xc":
            gains = [xp_of[cap][g] for g, cap in enumerate(plan.captains)]
            g = max(range(len(gws)), key=lambda i: gains[i])
            double = n_fix(plan.captains[g], g) >= 2
            reason = ("Your captain has two fixtures" if double else
                      "Save it for a captain with a double gameweek")
        elif chip == "bboost":
            gains = [sum(xp_of[p][g] for p in plan.squad if p not in set(plan.lineups[g])) for g in range(len(gws))]
            g = max(range(len(gws)), key=lambda i: gains[i])
            doubles = sum(1 for p in plan.squad if n_fix(p, g) >= 2)
            double = doubles >= BB_MIN_DOUBLES
            reason = (f"{doubles} of your squad have two fixtures" if double else
                      f"Save it for a double gameweek ({BB_MIN_DOUBLES}+ of your squad with two fixtures)")
        elif chip == "freehit":
            blanks = [sum(1 for p in hold.lineups[0] if n_fix(p, g) == 0) for g in range(len(gws))]
            g = max(range(len(gws)), key=lambda i: blanks[i])
            gains = [float(b) for b in blanks]
            double = blanks[g] >= FH_MIN_BLANKS
            reason = (f"{blanks[g]} of your starters have no fixture" if double else
                      f"Save it for a blank gameweek ({FH_MIN_BLANKS}+ starters without a fixture)")
        else:  # wildcard
            if wildcard_points is None:
                continue
            gain = round(wildcard_points - plan.expected_points, 1)
            g, gains = 0, [gain] * len(gws)
            double = gain >= WILDCARD_GAIN
            reason = (f"A rebuild adds {gain} expected points over {len(gws)} gameweeks" if double else
                      f"A rebuild only adds {gain} expected points over {len(gws)} gameweeks "
                      f"(play at {WILDCARD_GAIN:g}+)")
        out.append({
            "chip": chip,
            "label": CHIP_LABELS[chip],
            "best_gameweek": gws[g],
            "value": round(gains[g], 1),
            "play_now": bool(double) and g == 0,
            "play_in_horizon": bool(double),
            "reason": reason,
        })
    return out
