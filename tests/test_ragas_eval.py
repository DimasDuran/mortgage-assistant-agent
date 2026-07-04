"""Tests for the Ragas-based agent evaluation layer.

Unit tests for the message converter and scenario definitions (no LLM, no
network). The full regression test hits the real model and is gated by
``VERA_RUN_LIVE_TESTS=1``.
"""

import os

import pytest
from langchain_core.messages import (
    AIMessage as LCAIMessage,
)
from langchain_core.messages import (
    HumanMessage as LCHumanMessage,
)
from langchain_core.messages import (
    SystemMessage,
)
from langchain_core.messages import (
    ToolMessage as LCToolMessage,
)

from vera.evals.ragas_cases import SCENARIOS
from vera.evals.ragas_eval import _to_ragas_messages


def test_scenarios_are_defined():
    assert len(SCENARIOS) > 0
    ids = [s.id for s in SCENARIOS]
    assert len(ids) == len(set(ids)), "scenario IDs must be unique"


def test_scenarios_have_messages():
    for s in SCENARIOS:
        assert len(s.messages) > 0, f"{s.id} needs at least one message"


def test_scenarios_have_at_least_one_reference():
    for s in SCENARIOS:
        has = (
            s.reference_topics is not None
            or s.reference_tool_calls is not None
            or s.reference is not None
        )
        assert has, f"{s.id} must define at least one reference field"


def test_convert_empty_list():
    assert _to_ragas_messages([]) == []


def test_convert_skips_system_message():
    lc = [SystemMessage(content="You are a helpful assistant.")]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 0


def test_convert_human_message():
    lc = [LCHumanMessage(content="hello")]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 1
    assert ragas[0].content == "hello"


def test_convert_ai_message():
    lc = [LCAIMessage(content="hi there")]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 1
    assert ragas[0].content == "hi there"


def test_convert_ai_message_with_tool_calls():
    lc = [
        LCAIMessage(
            content="Let me calculate that.",
            tool_calls=[
                {
                    "name": "calculate_ltv",
                    "args": {"loan_amount": 900000, "property_value": 1000000},
                    "id": "call_123",
                    "type": "tool_call",
                }
            ],
        )
    ]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 1
    assert len(ragas[0].tool_calls) == 1
    assert ragas[0].tool_calls[0].name == "calculate_ltv"
    assert ragas[0].tool_calls[0].args["loan_amount"] == 900000


def test_convert_tool_message():
    lc = [LCToolMessage(content="LTV result: 90%", tool_call_id="call_123")]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 1
    assert "LTV" in ragas[0].content


def test_convert_full_conversation():
    from ragas.messages import HumanMessage as RagasHumanMessage

    lc = [
        SystemMessage(content="system prompt"),
        LCHumanMessage(content="What is my LTV?"),
        LCAIMessage(
            content="Calculating...",
            tool_calls=[
                {
                    "name": "calculate_ltv",
                    "args": {"loan_amount": 900000, "property_value": 1000000},
                    "id": "c1",
                    "type": "tool_call",
                }
            ],
        ),
        LCToolMessage(content="90%", tool_call_id="c1"),
        LCAIMessage(content="Your LTV is 90%."),
        LCHumanMessage(content="Thanks!"),
    ]
    ragas = _to_ragas_messages(lc)
    assert len(ragas) == 5  # system skipped
    assert isinstance(ragas[0], RagasHumanMessage)
    assert ragas[1].tool_calls[0].name == "calculate_ltv"
    assert "90%" in ragas[3].content


@pytest.mark.skipif(
    os.getenv("VERA_RUN_LIVE_TESTS") != "1",
    reason="live test: set VERA_RUN_LIVE_TESTS=1 (uses real keys and network)",
)
def test_ragas_eval_regression():
    from vera.core.config import get_settings
    from vera.evals.ragas_eval import evaluate_all

    get_settings.cache_clear()
    results = evaluate_all()
    assert len(results) == len(SCENARIOS)
    for r in results:
        assert r.error is None, f"{r.id} failed: {r.error}"
