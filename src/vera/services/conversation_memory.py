"""Per-thread conversation memory with automatic summarization.

Splits memory into two levels (like the Module-7 pattern):
  - **Long-term**: a compressed summary of early turns, stored externally.
  - **Short-term**: the most recent N message pairs, kept verbatim in the
    checkpoint via ``LangGraph.update_state``.

The summary is injected as a ``SystemMessage`` *before* the user message on
each turn so the agent always has the full context without unbounded growth.
"""

import logging
from typing import Any

from langchain_core.messages import BaseMessage

from vera.core.config import Settings
from vera.llm.model import build_model

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """You are a conversation summarizer for a mortgage-assistant \
AI. Given the conversation below, produce a concise summary that preserves:
- The user's name and key personal details they shared.
- Questions asked and answers given.
- Any decisions, status changes, or actions taken.
- Mortgage-specific facts (loan amounts, property details, financial figures).

Write in the same language as the conversation. Keep it under 200 words.
Omit greetings, pleasantries, and redundant information.

Conversation:
{text}"""


class ConversationMemory:
    """Manages per-thread summaries and triggers summarization."""

    def __init__(
        self,
        model_name: str,
        max_turns_before_summary: int = 6,
        keep_recent_turns: int = 2,
    ) -> None:
        self._summaries: dict[str, str] = {}
        self.model_name = model_name
        self.max_turns = max_turns_before_summary
        self.keep_recent = keep_recent_turns
        # Model used only for summarization calls (created lazily).
        self._summarizer: Any = None

    def _get_summarizer(self) -> Any:
        if self._summarizer is None:
            self._summarizer = build_model(Settings())
        return self._summarizer

    def get_summary(self, thread_id: str) -> str | None:
        return self._summaries.get(thread_id)

    def set_summary(self, thread_id: str, summary: str) -> None:
        self._summaries[thread_id] = summary

    def should_summarize(self, messages: list) -> bool:
        """Check if the conversation has grown past the threshold.

        Counts user+AI message pairs (each turn adds at least 2 messages).
        """
        return len(messages) > self.max_turns * 2

    def summarize_conversation(
        self, messages: list[BaseMessage]
    ) -> str:
        """Call the LLM to produce a compressed summary of old messages."""
        text = _messages_to_text(messages)
        prompt = _SUMMARIZE_PROMPT.format(text=text)
        model = self._get_summarizer()
        try:
            response = model.invoke(prompt)
            summary = (
                response.content if hasattr(response, "content") else str(response)
            )
            logger.info(
                "Summarized %d messages into %d chars", len(messages), len(summary)
            )
            return summary
        except Exception:
            logger.exception("Summarization failed; keeping full history.")
            return self.get_summary("_last") or ""


def _messages_to_text(messages: list[BaseMessage]) -> str:
    """Turn a list of LangChain messages into plain text for summarization."""
    parts = []
    for msg in messages:
        role = msg.type.upper() if hasattr(msg, "type") else "UNKNOWN"
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
            )
        parts.append(f"{role}: {content}")
    return "\n\n".join(parts)
