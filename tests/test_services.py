"""Application service tests (create case, fill sections)."""

import pytest

from vera.domain.models import BorrowerInformation, Name
from vera.domain.status import InvalidStatusTransition
from vera.repositories.memory import InMemoryApplicationRepository
from vera.services import applications as svc


def test_create_and_fill_flow():
    repo = InMemoryApplicationRepository()
    case = svc.create_application(repo, "ORG-1", name="Ana - home purchase")
    assert case.status == "draft"
    assert case.organization_id == "ORG-1"
    assert case.id.startswith("APP-")

    borrower = BorrowerInformation(name=Name(first="Ana"))
    updated = svc.update_borrower(repo, case.id, borrower)
    assert updated.borrower is not None
    assert updated.borrower.full_name == "Ana"

    reloaded = svc.get_application(repo, case.id)
    assert reloaded is not None
    assert reloaded.borrower is not None
    assert len(svc.list_applications(repo).items) == 1


def test_update_missing_raises():
    repo = InMemoryApplicationRepository()
    with pytest.raises(svc.ApplicationNotFoundError):
        svc.update_borrower(repo, "NOPE", BorrowerInformation(name=Name(first="X")))


def test_set_status_enforces_state_machine():
    repo = InMemoryApplicationRepository()
    case = svc.create_application(repo, "ORG-1")  # starts as draft

    moved = svc.set_status(repo, case.id, "invited")
    assert moved.status == "invited"

    with pytest.raises(InvalidStatusTransition):
        svc.set_status(repo, case.id, "approved")  # illegal jump from invited
