"""LangSmith Prompt Hub integration for the system prompt.

Code is the source of truth and the fallback. When use_prompt_hub is enabled,
the system prompt is pulled from the Hub at build time so it can be changed
without a code deploy; if the pull fails, we fall back to the code constant.

Push the current code prompt to the Hub with:  python -m vera.prompts.hub
"""

import contextlib

from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

from vera.core.config import get_settings
from vera.prompts.system import SYSTEM_PROMPT

PROMPT_NAME = "vera-system"


def push_system_prompt(client: Client | None = None) -> str:
    """Push the code system prompt to the LangSmith Prompt Hub."""
    client = client or Client()
    template = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT)])
    client.push_prompt(
        PROMPT_NAME,
        object=template,
        description="Vera mortgage assistant system prompt",
    )
    return PROMPT_NAME


def get_system_prompt() -> str:
    """Return the system prompt: from the Hub if enabled, else from code."""
    settings = get_settings()
    if not settings.use_prompt_hub:
        return SYSTEM_PROMPT
    with contextlib.suppress(Exception):
        pulled = Client().pull_prompt(PROMPT_NAME)
        messages = pulled.format_messages()
        if messages:
            return str(messages[0].content)
    return SYSTEM_PROMPT  # fallback to code on any failure


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    name = push_system_prompt()
    print(f"Pushed the system prompt to the LangSmith Prompt Hub as '{name}'.")


if __name__ == "__main__":
    main()
