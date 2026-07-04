"""Application lifecycle state machine.

Encodes the allowed status transitions for the no-account origination flow.
Keeping them here (instead of letting any caller set any status) prevents
illegal jumps such as draft straight to approved, and gives the corrections
loop an explicit resting state ("corrections_needed") to live in.
"""

from vera.domain.enums import ApplicationStatus

# Each status maps to the statuses it may move to next. The corrections loop is
# auto_review -> corrections_needed -> in_progress; the loan officer may also
# send an application back for corrections during review.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    "draft": frozenset({"invited"}),
    "invited": frozenset({"in_progress"}),
    "in_progress": frozenset({"submitted"}),
    "submitted": frozenset({"signed"}),
    "signed": frozenset({"auto_review"}),
    "auto_review": frozenset({"corrections_needed", "ready_for_loan_officer"}),
    "corrections_needed": frozenset({"in_progress"}),
    "ready_for_loan_officer": frozenset({"under_review"}),
    "under_review": frozenset({"approved", "rejected", "corrections_needed"}),
    "approved": frozenset(),
    "rejected": frozenset(),
}

TERMINAL_STATUSES: frozenset[ApplicationStatus] = frozenset({"approved", "rejected"})


class InvalidStatusTransition(Exception):
    """Raised when a status change is not allowed by the state machine."""

    def __init__(self, current: ApplicationStatus, target: ApplicationStatus) -> None:
        super().__init__(f"cannot move from '{current}' to '{target}'")
        self.current = current
        self.target = target


def can_transition(current: ApplicationStatus, target: ApplicationStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def ensure_transition(current: ApplicationStatus, target: ApplicationStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStatusTransition(current, target)
