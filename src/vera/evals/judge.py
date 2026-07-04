"""LLM-as-judge: score a reply against a case's success criteria.

Uses a cheaper Claude model with structured output, so the verdict is a typed
object, not free text we have to parse.
"""

from typing import cast

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from vera.core.config import get_settings


class JudgeVerdict(BaseModel):
    """The judge's decision for one case."""

    passed: bool = Field(description="True if the reply meets the criteria.")
    reason: str = Field(description="Short justification for the decision.")


_PROMPT = """You are strictly grading a mortgage assistant's reply.

Question:
{question}

Success criteria:
{criteria}

Assistant reply:
{answer}

Does the reply meet the criteria? Judge only against the criteria. If the reply
invents facts, answers off-topic, or gives binding advice when it should not, it
fails."""


def judge(question: str, answer: str, criteria: str) -> JudgeVerdict:
    """Return a pass/fail verdict for a single reply."""
    settings = get_settings()
    model = ChatAnthropic(
        model=settings.eval_judge_model,
        max_tokens=512,
        api_key=settings.anthropic_api_key,
        timeout=30,
    )
    structured = model.with_structured_output(JudgeVerdict)
    prompt = _PROMPT.format(question=question, criteria=criteria, answer=answer)
    return cast(JudgeVerdict, structured.invoke(prompt))
