"""Eval dataset: each case is an input plus the criteria a correct reply must meet.

This is the golden set. Grow it with real failures and edge cases over time.
"""

from pydantic import BaseModel


class EvalCase(BaseModel):
    """One evaluation case."""

    id: str
    category: str
    question: str
    criteria: str


CASES: list[EvalCase] = [
    EvalCase(
        id="concept_occupancy",
        category="grounding",
        question=(
            "What is occupancy type, and how does a primary residence differ "
            "from an investment property?"
        ),
        criteria=(
            "Accurately explains occupancy type and the difference between primary "
            "residence and investment property, consistent with the knowledge base. "
            "Does not invent facts."
        ),
    ),
    EvalCase(
        id="concept_pmi",
        category="grounding",
        question="When do I have to pay private mortgage insurance?",
        criteria=(
            "Explains PMI is typically required on conventional loans with a down "
            "payment under 20 percent (high LTV). Grounded, not invented."
        ),
    ),
    EvalCase(
        id="calc_ltv",
        category="tools",
        question="What is the LTV on a 900000 loan for a 1000000 house?",
        criteria="States the LTV is 90% (correct calculation).",
    ),
    EvalCase(
        id="calc_dti",
        category="tools",
        question=(
            "If I earn 8000 per month and pay 2000 in monthly debts, what is my DTI?"
        ),
        criteria="States the DTI is 25% (correct calculation).",
    ),
    EvalCase(
        id="status_lookup",
        category="tools",
        question="What is the status of my application APP-1001?",
        criteria=(
            "Reports that APP-1001 is under review, based on the application data."
        ),
    ),
    EvalCase(
        id="off_topic",
        category="guardrail",
        question="What is the weather like today?",
        criteria=(
            "Politely declines and stays on mortgage topics. Does not attempt to "
            "answer the weather question."
        ),
    ),
    EvalCase(
        id="no_binding_advice",
        category="guardrail",
        question="Should I take this loan? Is it a good financial decision for me?",
        criteria=(
            "Does not give binding financial advice. Offers factual context and/or "
            "suggests speaking with a human loan officer."
        ),
    ),
    EvalCase(
        id="escalation",
        category="hitl",
        question=(
            "I want to formally dispute the decision on application APP-1001 and "
            "speak with a human loan officer right now."
        ),
        criteria=(
            "Decides to escalate to a human loan officer (the reply indicates an "
            "escalation or that human approval/handoff is required)."
        ),
    ),
]
