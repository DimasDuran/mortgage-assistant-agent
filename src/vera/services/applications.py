"""Application use cases: create a case and fill its sections progressively.

No authentication: a case is shared state that every party reads and updates
through these steps. The data lives in the configured repository (Supabase).
"""

import uuid
from typing import Any

from vera.domain.enums import ApplicationStatus
from vera.domain.models import (
    Application,
    BorrowerInformation,
    Declarations,
    FinancialProfile,
    Income,
    LoanAndProperty,
)
from vera.domain.status import ensure_transition
from vera.repositories.base import ApplicationRepository, PaginatedResult


class ApplicationNotFoundError(Exception):
    """Raised when an operation targets an application that does not exist."""


def _new_id() -> str:
    return f"APP-{uuid.uuid4().hex[:8].upper()}"


def create_application(
    repo: ApplicationRepository,
    organization_id: str,
    name: str | None = None,
) -> Application:
    """Create a new case (draft) for a tenant, with an optional name."""
    application = Application(id=_new_id(), organization_id=organization_id, name=name)
    repo.upsert(application)
    return application


def get_application(
    repo: ApplicationRepository, application_id: str
) -> Application | None:
    return repo.get(application_id)


def list_applications(
    repo: ApplicationRepository,
    organization_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> PaginatedResult:
    return repo.list(organization_id, limit=limit, offset=offset)


def _update(
    repo: ApplicationRepository, application_id: str, **fields: Any
) -> Application:
    application = repo.get(application_id)
    if application is None:
        raise ApplicationNotFoundError(application_id)
    updated = application.model_copy(update=fields)
    repo.upsert(updated)
    return updated


def update_borrower(
    repo: ApplicationRepository, application_id: str, borrower: BorrowerInformation
) -> Application:
    return _update(repo, application_id, borrower=borrower)


def update_income(
    repo: ApplicationRepository, application_id: str, income: Income
) -> Application:
    return _update(repo, application_id, income=income)


def update_financial_profile(
    repo: ApplicationRepository, application_id: str, profile: FinancialProfile
) -> Application:
    return _update(repo, application_id, financial_profile=profile)


def update_loan_property(
    repo: ApplicationRepository, application_id: str, loan_property: LoanAndProperty
) -> Application:
    return _update(repo, application_id, loan_property=loan_property)


def update_declarations(
    repo: ApplicationRepository, application_id: str, declarations: Declarations
) -> Application:
    return _update(repo, application_id, declarations=declarations)


def set_status(
    repo: ApplicationRepository, application_id: str, status: ApplicationStatus
) -> Application:
    """Move a case to a new status, enforcing the lifecycle state machine."""
    application = repo.get(application_id)
    if application is None:
        raise ApplicationNotFoundError(application_id)
    ensure_transition(application.status, status)
    updated = application.model_copy(update={"status": status})
    repo.upsert(updated)
    return updated
