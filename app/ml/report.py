"""
Run the next-gameweek backtest against the live FPL API and print the report.

    python -m app.ml.report            # needs network access to fantasy.premierleague.com

Prints MAE per player-fixture and the mean actual points of each method's
top-50 picks for the last three completed rounds, versus naive baselines.
"""

import asyncio
import json

from ..config import settings
from ..services.data_service import FPLDataService
from ..services.prediction_service import PredictionService


async def main() -> None:
    settings.PREDICTION_MODEL = "next_gw"  # report regardless of the auto gate
    svc = PredictionService()
    await svc.refresh_next_gw(FPLDataService())
    info = await svc.get_model_info()
    print(json.dumps(info["models"]["next_gw"], indent=2))
    report = info["models"]["next_gw"].get("backtest")
    if report:
        verdict = "BEATS" if report["beats_baselines"] else "does NOT beat"
        print(f"\nModel {verdict} the naive baselines on rounds {report['test_rounds']}.")


if __name__ == "__main__":
    asyncio.run(main())
