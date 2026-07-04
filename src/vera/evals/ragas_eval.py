# ruff: isort: skip_file
"""Evaluate Vera agent with Ragas metrics (tool-call quality, topic, goals).

Uses the same agent and settings as the existing eval suite but evaluates
multi-turn conversations with structured Ragas metrics:

- **ToolCallAccuracy**: did the agent call the right tools in the right order?
- **ToolCallF1**: precision/recall of tool calls vs expected calls.
- **TopicAdherence**: does the conversation stay on mortgage topics?
- **AgentGoalAccuracyWithReference**: did the agent achieve the stated goal?

Run::

    python -m vera.evals.ragas_eval

Requires ``ANTHROPIC_API_KEY`` in the environment (used by both the agent and
the Ragas evaluator LLM).
"""

import asyncio
import logging
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage as LCAIMessage,
    HumanMessage as LCHumanMessage,
    SystemMessage,
    ToolMessage as LCToolMessage,
)
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

import vera.evals._ragas_compat  # noqa: F401  # must be before ragas

from ragas.llms import LangchainLLMWrapper
from ragas.messages import AIMessage, HumanMessage, ToolCall, ToolMessage

from vera.agents.agent import build_agent
from vera.app import _build_messages, _get_memory, _maybe_summarize
from vera.core.config import get_settings
from vera.evals.ragas_cases import SCENARIOS, RagasScenario

logger = logging.getLogger(__name__)


class RagasEvalResult(BaseModel):
    """Outcome of one Ragas evaluation across all applicable metrics."""

    id: str
    category: str
    tool_call_accuracy: float | None = None
    tool_call_f1: float | None = None
    topic_adherence: float | None = None
    agent_goal_accuracy: float | None = None
    error: str | None = None


def _to_ragas_messages(lc_messages: list) -> list:
    """Convert LangChain messages to the Ragas message format.

    Skips ``SystemMessage`` (Ragas only evaluates the conversation turns)
    and maps Human / AI / Tool messages with their tool-call metadata.
    """
    result: list = []
    for msg in lc_messages:
        if isinstance(msg, SystemMessage):
            continue
        if isinstance(msg, LCHumanMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            result.append(HumanMessage(content=content))
        elif isinstance(msg, LCAIMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            tool_calls_raw = msg.tool_calls or []
            tool_calls = [
                ToolCall(name=tc["name"], args=tc["args"])
                for tc in tool_calls_raw
            ]
            result.append(AIMessage(content=content, tool_calls=tool_calls))
        elif isinstance(msg, LCToolMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            result.append(ToolMessage(content=content))
    return result


def _run_scenario(
    agent: Runnable, scenario: RagasScenario, thread_id: str
) -> list:
    """Run the agent through the scenario's conversation turns.

    Returns the full message history converted to the Ragas format.
    """
    memory = _get_memory()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    for msg in scenario.messages:
        payload = {"messages": _build_messages(msg, thread_id, memory)}
        result = agent.invoke(payload, config)
        _maybe_summarize(agent, config, result, thread_id, memory)

    try:
        state = agent.get_state(config)
        all_messages = state.values.get("messages", [])
    except Exception:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": ""}]}, config
        )
        all_messages = result.get("messages", [])

    return _to_ragas_messages(all_messages)


def _build_evaluator_llm() -> Any:
    """Build a Ragas-compatible LLM wrapper using the eval judge model."""
    settings = get_settings()
    chat = ChatAnthropic(
        model=settings.eval_judge_model,
        api_key=settings.anthropic_api_key,
        timeout=30,
    )
    return LangchainLLMWrapper(chat)


async def _evaluate_scenario(
    ragas_messages: list,
    scenario: RagasScenario,
    llm: Any,
) -> RagasEvalResult:
    """Run all applicable Ragas metrics on one scenario."""
    from ragas.metrics.collections import (
        AgentGoalAccuracyWithReference,
        ToolCallAccuracy,
        ToolCallF1,
        TopicAdherence,
    )

    kwargs: dict[str, Any] = {"id": scenario.id, "category": scenario.category}

    try:
        if scenario.reference_tool_calls is not None:
            metric_acc = ToolCallAccuracy()
            result_acc = await metric_acc.ascore(
                user_input=ragas_messages,
                reference_tool_calls=scenario.reference_tool_calls,
            )
            kwargs["tool_call_accuracy"] = result_acc.value

            if scenario.reference_tool_calls:
                metric_f1 = ToolCallF1()
                result_f1 = await metric_f1.ascore(
                    user_input=ragas_messages,
                    reference_tool_calls=scenario.reference_tool_calls,
                )
                kwargs["tool_call_f1"] = result_f1.value

        if scenario.reference_topics is not None:
            metric_topic = TopicAdherence(llm=llm, mode="precision")
            result_topic = await metric_topic.ascore(
                user_input=ragas_messages,
                reference_topics=scenario.reference_topics,
            )
            kwargs["topic_adherence"] = result_topic.value

        if scenario.reference is not None:
            metric_goal = AgentGoalAccuracyWithReference(llm=llm)
            result_goal = await metric_goal.ascore(
                user_input=ragas_messages,
                reference=scenario.reference,
            )
            kwargs["agent_goal_accuracy"] = result_goal.value

    except Exception as exc:
        kwargs["error"] = str(exc)
        logger.exception("Ragas eval failed for %s", scenario.id)

    return RagasEvalResult(**kwargs)


def evaluate_all() -> list[RagasEvalResult]:
    """Run all Ragas scenarios synchronously and return results."""

    async def _run_all() -> list[RagasEvalResult]:
        settings = get_settings()
        agent = build_agent()
        llm = _build_evaluator_llm()
        results: list[RagasEvalResult] = []

        for scenario in SCENARIOS:
            ragas_messages = _run_scenario(
                agent, scenario, f"ragas-{scenario.id}"
            )
            result = await _evaluate_scenario(ragas_messages, scenario, llm)
            results.append(result)

            if settings.eval_delay_seconds:
                await asyncio.sleep(settings.eval_delay_seconds)

        return results

    return asyncio.run(_run_all())


def print_results(results: list[RagasEvalResult]) -> None:
    """Pretty-print Ragas evaluation results."""
    print(f"\n{'=' * 72}")
    print(f"{'RAGAS AGENT EVALUATION':^72}")
    print(f"{'=' * 72}")

    for r in results:
        if r.error:
            print(f"\n[{r.id}] ({r.category}) ERROR: {r.error}")
            continue
        scores = []
        if r.tool_call_accuracy is not None:
            scores.append(f"acc={r.tool_call_accuracy:.2f}")
        if r.tool_call_f1 is not None:
            scores.append(f"f1={r.tool_call_f1:.2f}")
        if r.topic_adherence is not None:
            scores.append(f"topic={r.topic_adherence:.2f}")
        if r.agent_goal_accuracy is not None:
            scores.append(f"goal={r.agent_goal_accuracy:.2f}")
        print(f"  [{r.id:<30}] ({r.category:<12}) {' | '.join(scores)}")

    mean_metrics = _mean_scores(results)
    if mean_metrics:
        print(f"\n{'─' * 72}")
        print("  MEAN SCORES:")
        for name, value in mean_metrics.items():
            print(f"    {name:<30} {value:.3f}")
    print()


def _mean_scores(results: list[RagasEvalResult]) -> dict[str, float]:
    """Aggregate mean scores per metric across all results (errors excluded)."""
    valid = [r for r in results if r.error is None]
    if not valid:
        return {}

    accum: dict[str, list[float]] = {}
    fields = [
        "tool_call_accuracy",
        "tool_call_f1",
        "topic_adherence",
        "agent_goal_accuracy",
    ]
    for f in fields:
        values = [getattr(r, f) for r in valid if getattr(r, f) is not None]
        if values:
            accum[f] = values

    return {name: sum(vals) / len(vals) for name, vals in accum.items()}


def main() -> None:
    load_dotenv()
    results = evaluate_all()
    print_results(results)


if __name__ == "__main__":
    main()
