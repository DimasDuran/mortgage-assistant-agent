"""Tests for the application lifecycle state machine."""

from itertools import pairwise

import pytest

from vera.domain.status import (
    ALLOWED_TRANSITIONS,
    InvalidStatusTransition,
    can_transition,
    ensure_transition,
)


def test_happy_path_transitions_are_allowed():
    path = [
        "draft",
        "invited",
        "in_progress",
        "submitted",
        "signed",
        "auto_review",
        "ready_for_loan_officer",
        "under_review",
        "approved",
    ]
    for current, target in pairwise(path):
        assert can_transition(current, target)


def test_corrections_loop():
    assert can_transition("auto_review", "corrections_needed")
    assert can_transition("corrections_needed", "in_progress")


def test_illegal_jump_is_rejected():
    assert not can_transition("draft", "approved")
    with pytest.raises(InvalidStatusTransition):
        ensure_transition("draft", "approved")


def test_terminal_statuses_have_no_transitions():
    assert ALLOWED_TRANSITIONS["approved"] == frozenset()
    assert ALLOWED_TRANSITIONS["rejected"] == frozenset()
