"""Run the eval suite against the agent and report a pass rate.

Run manually (or in a scheduled CI job with the API keys set):
    python -m vera.evals.run
"""

import time

from dotenv import load_dotenv
from pydantic import BaseModel

from vera.agents.agent import build_agent
from vera.app import chat
from vera.core.config import get_settings
from vera.evals.cases import CASES, EvalCase
from vera.evals.judge import judge


class EvalResult(BaseModel):
    """The outcome of one eval case."""

    id: str
    category: str
    passed: bool
    reason: str
    answer: str


def run_evals(cases: list[EvalCase] | None = None) -> list[EvalResult]:
    """Run each case through the agent, judge the reply, and collect results."""
    cases = cases or CASES
    settings = get_settings()
    agent = build_agent()

    results: list[EvalResult] = []
    for index, case in enumerate(cases):
        answer, _usage = chat(agent, case.question, f"eval-{case.id}")
        verdict = judge(case.question, answer, case.criteria)
        results.append(
            EvalResult(
                id=case.id,
                category=case.category,
                passed=verdict.passed,
                reason=verdict.reason,
                answer=answer,
            )
        )
        # Space calls out to respect the embedding provider's free-tier rate limit.
        if settings.eval_delay_seconds and index < len(cases) - 1:
            time.sleep(settings.eval_delay_seconds)
    return results


def pass_rate(results: list[EvalResult]) -> float:
    """Fraction of cases that passed (0.0 if there are none)."""
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)


def main() -> None:
    load_dotenv()
    results = run_evals()
    for result in results:
        mark = "PASS" if result.passed else "FAIL"
        print(f"[{mark}] {result.id} ({result.category}) - {result.reason}")
    print(f"\nPass rate: {pass_rate(results):.0%} ({len(results)} cases)")


if __name__ == "__main__":
    main()
