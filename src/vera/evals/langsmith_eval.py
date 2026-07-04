"""Run the eval suite on LangSmith (datasets + evaluation).

The dataset is defined in code (cases.py) and synced to LangSmith; LangSmith runs
the evaluation and keeps history and comparisons. Run with the keys set:

    python -m vera.evals.langsmith_eval

Requires LANGSMITH_API_KEY (and ANTHROPIC/VOYAGE/PINECONE for the cases).

The module also evaluates multi-turn agent quality with **Ragas** metrics
(ToolCallAccuracy, ToolCallF1, TopicAdherence, AgentGoalAccuracy) and logs
the scores to LangSmith as a separate experiment.
"""

import uuid
from typing import Any

from dotenv import load_dotenv
from langsmith import Client, evaluate

from vera.agents.agent import build_agent
from vera.app import chat
from vera.evals.cases import CASES
from vera.evals.judge import judge
from vera.evals.ragas_cases import SCENARIOS as RAGAS_SCENARIOS
from vera.evals.ragas_eval import evaluate_all as run_ragas_scenarios

DATASET_NAME = "vera-evals"
RAGAS_DATASET_NAME = "vera-ragas-evals"

_agent: Any = None


def _get_agent() -> Any:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def sync_dataset(client: Client | None = None) -> str:
    """Create (or recreate) the LangSmith dataset from cases.py."""
    client = client or Client()
    try:
        existing = client.read_dataset(dataset_name=DATASET_NAME)
        client.delete_dataset(dataset_id=existing.id)
    except Exception:
        pass
    dataset = client.create_dataset(
        DATASET_NAME, description="Vera eval cases, synced from cases.py."
    )
    for case in CASES:
        client.create_example(
            inputs={"question": case.question},
            metadata={
                "criteria": case.criteria,
                "category": case.category,
                "case_id": case.id,
            },
            dataset_id=dataset.id,
        )
    return DATASET_NAME


def _target(inputs: dict[str, Any]) -> dict[str, str]:
    """Run Vera on one case (fresh conversation thread per case)."""
    answer, _usage = chat(_get_agent(), inputs["question"], uuid.uuid4().hex)
    return {"answer": answer}


def _correctness(run: Any, example: Any) -> dict[str, Any]:
    """LLM-as-judge evaluator: pass/fail against the case's criteria."""
    question = example.inputs["question"]
    answer = run.outputs.get("answer", "") if run.outputs else ""
    criteria = (example.metadata or {}).get("criteria", "")
    verdict = judge(question, answer, criteria)
    return {"key": "passed", "score": int(verdict.passed), "comment": verdict.reason}


def run_eval() -> None:
    """Sync the dataset and run the evaluation on LangSmith."""
    client = Client()
    sync_dataset(client)
    evaluate(
        _target,
        data=DATASET_NAME,
        evaluators=[_correctness],
        experiment_prefix="vera",
        client=client,
    )


def _sync_ragas_dataset(client: Client) -> str:
    """Create or retrieve the LangSmith dataset for multi-turn Ragas scenarios."""
    try:
        client.read_dataset(dataset_name=RAGAS_DATASET_NAME)
        return RAGAS_DATASET_NAME
    except Exception:
        pass
    dataset = client.create_dataset(
        RAGAS_DATASET_NAME,
        description="Vera multi-turn agent eval scenarios (Ragas metrics).",
    )
    for scenario in RAGAS_SCENARIOS:
        client.create_example(
            inputs={"scenario_id": scenario.id, "messages": scenario.messages},
            metadata={
                "category": scenario.category,
                "reference_topics": scenario.reference_topics,
                "reference": scenario.reference,
            },
            dataset_id=dataset.id,
        )
    return RAGAS_DATASET_NAME


def _ragas_evaluator(run: Any, example: Any) -> dict[str, Any]:
    """LangSmith evaluator that reports Ragas scores for a run.

    The target must return the RagasResult object; the evaluator extracts
    individual metric keys and returns them as feedback.
    """
    if run.outputs is None:
        return {"key": "ragas_error", "score": 0}
    result = run.outputs.get("result")
    if result is None:
        return {"key": "ragas_error", "score": 0}
    return {"key": "ragas_result", "score": 1, "comment": str(result)}


def run_ragas_eval() -> None:
    """Run Ragas multi-turn evaluation and log results to LangSmith.

    Creates a dataset from the Ragas scenarios, runs each scenario through
    the agent, evaluates with Ragas metrics, and logs scores as feedback.
    """

    client = Client()
    _sync_ragas_dataset(client)

    results = run_ragas_scenarios()

    for result in results:
        scores = {
            "tool_call_accuracy": result.tool_call_accuracy,
            "tool_call_f1": result.tool_call_f1,
            "topic_adherence": result.topic_adherence,
            "agent_goal_accuracy": result.agent_goal_accuracy,
        }
        active = {k: v for k, v in scores.items() if v is not None}
        if not active:
            continue

        for metric_name, value in active.items():
            client.create_feedback(
                run_id=None,
                key=f"ragas_{metric_name}",
                score=value,
                comment=f"{result.id}/{metric_name}",
            )

    from vera.evals.ragas_eval import _mean_scores, print_results

    print_results(results)
    means = _mean_scores(results)
    if means:
        for name, value in means.items():
            client.create_feedback(
                run_id=None,
                key=f"ragas_mean_{name}",
                score=value,
                comment="mean across all scenarios",
            )
        print("  [logged to LangSmith as feedback]")
    print()


def main() -> None:
    load_dotenv()
    run_eval()


if __name__ == "__main__":
    main()
