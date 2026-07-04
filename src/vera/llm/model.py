"""Chat model construction (ChatAnthropic) with caching support."""

from typing import Any

from langchain_anthropic import ChatAnthropic

from vera.core.config import Settings


class CachedChatAnthropic(ChatAnthropic):
    """Subclass that injects cache_control into the system prompt.

    Transforms ``system: "<text>"`` to a list block with
    ``cache_control: {"type": "ephemeral"}`` so every request asks
    Anthropic to cache the system prompt.
    """

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        system = payload.get("system")
        if not system:
            return payload
        if isinstance(system, str):
            if not system.strip():
                return payload
            payload["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        elif isinstance(system, list):
            for block in system:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                    and "cache_control" not in block
                    and block.get("text", "").strip()
                ):
                    block["cache_control"] = {"type": "ephemeral"}
                    break
        return payload


def build_model(settings: Settings) -> ChatAnthropic:
    """Build a ChatAnthropic instance with prompt caching enabled."""
    cls = CachedChatAnthropic if settings.enable_cache else ChatAnthropic
    return cls(
        model=settings.model,
        max_tokens=settings.max_tokens,
        api_key=settings.anthropic_api_key,
        timeout=30,
    )
