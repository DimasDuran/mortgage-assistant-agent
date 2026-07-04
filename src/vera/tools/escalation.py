"""Escalation tool: hand the conversation off to a human loan officer.

This is the sensitive action gated by human-in-the-loop approval (see the agent's
middleware): the agent proposes it, a human approves or rejects, and only then
does it run.

In production, calling this tool would create a support ticket (via
Zendesk/Linear/Intercom API), send a Slack/email notification to the assigned
loan officer, and persist the escalation reason so the audit trail is
preserved across agent restarts.
"""

from langchain_core.tools import tool


@tool
def escalate_to_loan_officer(
    reason: str, application_id: str | None = None
) -> dict[str, str]:
    """Hand off the conversation to a human loan officer.

    Use this for anything outside your scope: the user asks to speak to a person,
    wants a decision or an exception, disputes something, or requests an action you
    cannot perform. Give a short reason.

    Args:
        reason: why you are escalating.
        application_id: the related application id, if known.
    """
    return {
        "status": "escalated",
        "reason": reason,
        "application_id": application_id or "unknown",
        "message": "A loan officer has been notified and will follow up.",
    }
