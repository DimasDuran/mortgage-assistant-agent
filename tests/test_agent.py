"""Agent-level tests.

Building the agent does not call the API, so it runs in CI with a dummy key.
A real conversation is exercised by evals (later phase), not by unit tests.
"""

import os

import pytest

from vera.agents.agent import build_agent
from vera.core.config import get_settings


def test_agent_builds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    agent = build_agent()
    assert agent is not None
    assert hasattr(agent, "invoke")


@pytest.mark.skipif(
    os.getenv("VERA_RUN_LIVE_TESTS") != "1",
    reason="live test: set VERA_RUN_LIVE_TESTS=1 (uses real keys and network)",
)
def test_agent_responds():
    from vera.app import chat

    get_settings.cache_clear()
    agent = build_agent()
    reply = chat(agent, "What is the LTV for a 800000 loan on a 1000000 home?", "t1")
    assert "80" in reply
