"""Organization (tenant) use cases: create and read organizations."""

import uuid

from vera.domain.models import Organization
from vera.repositories.organizations import OrganizationRepository


class OrganizationNotFoundError(Exception):
    """Raised when an operation targets an organization that does not exist."""


def _new_id() -> str:
    return f"ORG-{uuid.uuid4().hex[:8].upper()}"


def create_organization(repo: OrganizationRepository, name: str) -> Organization:
    organization = Organization(id=_new_id(), name=name)
    repo.upsert(organization)
    return organization


def get_organization(
    repo: OrganizationRepository, organization_id: str
) -> Organization | None:
    return repo.get(organization_id)


def list_organizations(repo: OrganizationRepository) -> list[Organization]:
    return repo.list()
