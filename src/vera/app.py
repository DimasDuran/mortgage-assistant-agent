"""Entry points to run Vera from the command line."""

import logging
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.types import Command

from vera.agents.agent import build_agent
from vera.core.config import get_settings
from vera.prompts.system import SYSTEM_PROMPT
from vera.services.conversation_memory import ConversationMemory
from vera.services.cost_tracker import extract_usage_from_result

logger = logging.getLogger(__name__)


def _reply(result: dict[str, Any]) -> str:
    """Turn an agent result into text, flagging when human approval is needed."""
    interrupts = result.get("__interrupt__")
    if interrupts:
        return f"[APPROVAL REQUIRED] {interrupts[0].value}"
    return str(result["messages"][-1].content)


def _build_messages(
    message: str,
    thread_id: str,
    memory: ConversationMemory,
) -> list:
    """Build the messages list, injecting long-term summary if available."""
    summary = memory.get_summary(thread_id)
    system_content = SYSTEM_PROMPT
    if summary:
        system_content += f"\n\nPrevious conversation summary:\n{summary}"
    return [
        SystemMessage(content=system_content),
        {"role": "user", "content": message},
    ]


def _maybe_summarize(
    agent: Runnable,
    config: RunnableConfig,
    result: dict[str, Any],
    thread_id: str,
    memory: ConversationMemory,
) -> None:
    """After a turn, check if summarization is needed and trim state."""
    messages = result.get("messages", [])
    if not memory.should_summarize(messages):
        return
    keep = memory.keep_recent * 2
    old = messages[:-keep] if keep > 0 else []
    recent = messages[-keep:] if keep > 0 else messages
    if not old:
        return
    summary = memory.summarize_conversation(old)
    if summary:
        memory.set_summary(thread_id, summary)
        try:
            agent.update_state(config, {"messages": recent})  # type: ignore[attr-defined]
        except Exception:
            logger.warning("Could not trim checkpoint state", exc_info=True)


def chat(
    agent: Runnable, message: str, thread_id: str
) -> tuple[str, dict[str, int]]:
    """Send one message to the agent and return (reply, usage).

    `thread_id` selects the conversation; the checkpointer keeps its history. If
    the agent proposes a guarded action, the reply is flagged for approval and you
    continue with `resume`.
    """
    memory = _get_memory()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    payload = {"messages": _build_messages(message, thread_id, memory)}
    result = agent.invoke(payload, config)
    _maybe_summarize(agent, config, result, thread_id, memory)
    return _reply(result), extract_usage_from_result(result)


def resume(
    agent: Runnable,
    thread_id: str,
    *,
    approve: bool,
    message: str | None = None,
) -> tuple[str, dict[str, int]]:
    """Resume a conversation paused for human approval (human-in-the-loop)."""
    memory = _get_memory()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    decision: dict[str, Any] = (
        {"type": "approve"}
        if approve
        else {"type": "reject", "message": message or "Rejected by reviewer."}
    )
    result = agent.invoke(Command(resume={"decisions": [decision]}), config)
    _maybe_summarize(agent, config, result, thread_id, memory)
    return _reply(result), extract_usage_from_result(result)


_memory: ConversationMemory | None = None


def _get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        s = get_settings()
        _memory = ConversationMemory(
            model_name=s.model,
            max_turns_before_summary=s.max_turns_before_summary,
            keep_recent_turns=s.keep_recent_turns,
        )
    return _memory


def main() -> None:
    """Minimal demo. Requires ANTHROPIC_API_KEY in the environment.

    Loads .env so LangSmith tracing (LANGSMITH_* vars) is picked up automatically.
    """
    from vera.core.pricing import calculate_cost

    load_dotenv()
    settings = get_settings()
    logger.info(
        "Checkpointer: %s",
        "PostgresSaver" if settings.database_url else "MemorySaver",
    )
    agent = build_agent()
    question = "What does occupancy type mean on a mortgage application?"
    reply, usage = chat(agent, question, "demo")
    cost = calculate_cost("claude-sonnet-4-6", **usage)
    print(reply)
    print(
        f"\n---\n"
        f"Input tokens: {usage['input_tokens']:,}  "
        f"Output tokens: {usage['output_tokens']:,}  "
        f"Cache read: {usage['cache_read_input_tokens']:,}  "
        f"Cost: ${cost:.6f}"
    )


if __name__ == "__main__":
    main()
