import os

# Never hit the live FPL API from tests (startup pre-warm + next-GW refresh middleware).
os.environ.setdefault("SKIP_PREWARM", "true")
