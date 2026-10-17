import os

# Never hit the live FPL API from tests (startup pre-warm + next-GW refresh middleware).
os.environ.setdefault("SKIP_PREWARM", "true")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.reset()
    yield
