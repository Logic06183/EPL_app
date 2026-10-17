"""
FPL squad optimiser — exact integer programme (scipy / HiGHS).

Chooses a 15-player squad and its best starting XI jointly, enforcing the
official FPL rules:
  * squad: 2 GK, 5 DEF, 5 MID, 3 FWD; total cost <= budget; max 3 per club
  * XI: exactly 11 with 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD
Objective: maximise predicted XI points (captain counted twice) plus a small
weight on bench points so the bench isn't filled with dead money when
there's budget to spare.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

SQUAD_SLOTS = {1: 2, 2: 5, 3: 5, 4: 3}            # element_type -> squad count
XI_LIMITS   = {1: (1, 1), 2: (3, 5), 3: (2, 5), 4: (1, 3)}
MAX_PER_CLUB = 3
BENCH_WEIGHT = 0.1
POS_NAME = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


class InfeasibleSquad(ValueError):
    """No legal squad exists for the given budget / player pool."""


@dataclass(frozen=True)
class Candidate:
    id: int
    position: int      # 1..4
    club: int
    price: float       # £m
    predicted: float


@dataclass(frozen=True)
class SquadResult:
    squad_ids: list[int]
    starting_ids: list[int]
    captain_id: int
    total_cost: float


def optimise_squad(candidates: list[Candidate], budget: float) -> SquadResult:
    n = len(candidates)
    if n == 0:
        raise InfeasibleSquad("No players available")

    pred  = np.array([max(c.predicted, 0.0) for c in candidates])
    price = np.array([c.price for c in candidates])
    pos   = np.array([c.position for c in candidates])
    clubs = sorted({c.club for c in candidates})
    club  = np.array([c.club for c in candidates])

    # Variables: x (in squad) | y (in XI) | z (captain), each length n, binary.
    def block(x=None, y=None, z=None):
        row = np.zeros(3 * n)
        if x is not None:
            row[:n] = x
        if y is not None:
            row[n:2 * n] = y
        if z is not None:
            row[2 * n:] = z
        return row

    A, lo, hi = [], [], []

    def add(row, lower, upper):
        A.append(row)
        lo.append(lower)
        hi.append(upper)

    add(block(x=price), -np.inf, budget + 1e-6)
    for p, count in SQUAD_SLOTS.items():
        mask = (pos == p).astype(float)
        add(block(x=mask), count, count)
        add(block(y=mask), *XI_LIMITS[p])
    for c in clubs:
        add(block(x=(club == c).astype(float)), 0, MAX_PER_CLUB)
    add(block(y=np.ones(n)), 11, 11)
    add(block(z=np.ones(n)), 1, 1)
    # y_i <= x_i and z_i <= y_i
    eye = np.eye(n)
    link_xy = np.hstack([-eye, eye, np.zeros((n, n))])
    link_yz = np.hstack([np.zeros((n, n)), -eye, eye])

    constraints = [
        LinearConstraint(np.array(A), lo, hi),
        LinearConstraint(np.vstack([link_xy, link_yz]), -np.inf, 0),
    ]

    # milp minimises → negate. Squad term gives bench weight; XI adds the rest.
    c = -np.concatenate([BENCH_WEIGHT * pred, (1 - BENCH_WEIGHT) * pred, pred])
    res = milp(
        c,
        constraints=constraints,
        integrality=np.ones(3 * n),
        bounds=Bounds(0, 1),
        options={"time_limit": 10},
    )
    if res.x is None:
        raise InfeasibleSquad(f"No legal 15-player squad fits a £{budget:.1f}m budget")

    x = res.x[:n] > 0.5
    y = res.x[n:2 * n] > 0.5
    z = res.x[2 * n:] > 0.5
    ids = np.array([c.id for c in candidates])
    return SquadResult(
        squad_ids=ids[x].tolist(),
        starting_ids=ids[y].tolist(),
        captain_id=int(ids[z][0]),
        total_cost=round(float(price[x].sum()), 1),
    )
