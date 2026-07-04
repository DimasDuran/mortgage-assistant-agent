"""Vera agent, built with LangChain's prebuilt create_agent (on LangGraph)."""

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from vera.core.config import Settings, get_settings
from vera.llm.model import build_model
from vera.tools import get_tools

# Matches U.S. Social Security numbers like 123-45-6789.
_SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"


def build_agent(
    settings: Settings | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Runnable:
    """Build the Vera agent.

    The framework provides the agent loop, tool execution and persistence. We add
    middleware for the security and reliability concerns:
    - PII: redact emails and mask SSNs in both input and output.
    - Tool-call limit: cap the loop so the agent cannot run away.
    - Human-in-the-loop: require human approval before escalating to a loan officer.
    """
    settings = settings or get_settings()
    model = build_model(settings)
    middleware: list[AgentMiddleware] = [
        PIIMiddleware("email", strategy="redact", apply_to_output=True),
        PIIMiddleware(
            "ssn", detector=_SSN_PATTERN, strategy="mask", apply_to_output=True
        ),
        ToolCallLimitMiddleware(run_limit=settings.max_steps),  # type: ignore[list-item]
        HumanInTheLoopMiddleware(interrupt_on={"escalate_to_loan_officer": True}),
    ]
    return create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=None,
        middleware=middleware,
        checkpointer=checkpointer or MemorySaver(),
    )
