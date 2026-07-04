"""Regression gate: the eval suite must meet the pass-rate threshold.

This hits the real model and network, so it is skipped unless a real
ANTHROPIC_API_KEY is set. Run it locally or in a scheduled CI job with secrets.
"""

import os

import pytest

from vera.core.config import get_settings
from vera.evals.run import pass_rate, run_evals


@pytest.mark.skipif(
    os.getenv("VERA_RUN_LIVE_TESTS") != "1",
    reason="live test: set VERA_RUN_LIVE_TESTS=1 (uses real keys and network)",
)
def test_eval_regression() -> None:
    get_settings.cache_clear()
    results = run_evals()
    rate = pass_rate(results)
    failed = [r.id for r in results if not r.passed]
    assert rate >= get_settings().eval_threshold, (
        f"Eval pass rate {rate:.0%} below threshold "
        f"{get_settings().eval_threshold:.0%}; failed: {failed}"
    )
