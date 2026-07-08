"""Vera agent, built with LangChain's prebuilt create_agent (on LangGraph)."""

import logging

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

logger = logging.getLogger(__name__)

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

    If no checkpointer is provided, the function attempts to create a PostgresSaver
    from settings.database_url. Falls back to MemorySaver if Postgres is unavailable.
    """
    settings = settings or get_settings()
    model = build_model(settings)
    middleware: list[AgentMiddleware] = [
        PIIMiddleware("email", strategy="redact", apply_to_output=True),
        PIIMiddleware(
            "ssn", detector=_SSN_PATTERN, strategy="mask", apply_to_output=True
        ),
        ToolCallLimitMiddleware(run_limit=settings.max_steps),
        HumanInTheLoopMiddleware(interrupt_on={"escalate_to_loan_officer": True}),
    ]
    return create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=None,
        middleware=middleware,
        checkpointer=checkpointer or _create_checkpointer(settings),
    )


def _create_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Create a persistent Postgres checkpointer, or fall back to MemorySaver.

    Uses the DATABASE_URL from settings. If not configured or connection fails,
    falls back to in-memory (safe for development, lost on restart).
    """
    db_url = settings.database_url
    if not db_url:
        logger.info("No DATABASE_URL set, using MemorySaver (state lost on restart)")
        return MemorySaver()

    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        logger.warning(
            "psycopg or langgraph-checkpoint-postgres not installed, "
            "using MemorySaver"
        )
        return MemorySaver()

    try:
        conn = psycopg.connect(db_url, connect_timeout=10)
        saver = PostgresSaver(conn)  # type: ignore[arg-type]
        saver.setup()  # creates checkpoint tables if they don't exist
        logger.info("Postgres checkpointer ready (DATABASE_URL configured)")
        return saver
    except (psycopg.Error, OSError):
        logger.warning(
            "Failed to connect Postgres checkpointer, falling back to MemorySaver",
            exc_info=True,
        )
        if "conn" in locals() and conn is not None:
            conn.close()
        return MemorySaver()
