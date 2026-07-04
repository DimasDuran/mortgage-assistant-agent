"""Organization (tenant) repository: port, adapters, and selection.

Mirrors the application repository: Supabase when configured, otherwise an
in-memory store seeded with a demo organization (development and tests).
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, cast

from vera.core.config import Settings, get_settings
from vera.domain.models import Organization


class OrganizationRepository(ABC):
    """Read and write organizations (tenants)."""

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def upsert(self, organization: Organization) -> None: ...

    @abstractmethod
    def list(self) -> list[Organization]: ...


class InMemoryOrganizationRepository(OrganizationRepository):
    """Keeps organizations in a dict. Lost on restart; not for production."""

    def __init__(self, seed: dict[str, Organization] | None = None) -> None:
        self._store: dict[str, Organization] = dict(seed or {})

    def get(self, organization_id: str) -> Organization | None:
        return self._store.get(organization_id)

    def upsert(self, organization: Organization) -> None:
        self._store[organization.id] = organization

    def list(self) -> list[Organization]:
        return list(self._store.values())


class SupabaseOrganizationRepository(OrganizationRepository):
    """Read/write organizations in Supabase Postgres."""

    def __init__(self, client: Any, table: str) -> None:
        self._client = client
        self._table = table

    def get(self, organization_id: str) -> Organization | None:
        response = (
            self._client.table(self._table)
            .select("id, name")
            .eq("id", organization_id)
            .limit(1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], response.data)
        return Organization.model_validate(rows[0]) if rows else None

    def upsert(self, organization: Organization) -> None:
        self._client.table(self._table).upsert(
            {"id": organization.id, "name": organization.name}
        ).execute()

    def list(self) -> list[Organization]:
        response = self._client.table(self._table).select("id, name").execute()
        rows = cast(list[dict[str, Any]], response.data)
        return [Organization.model_validate(row) for row in rows]


def demo_organizations() -> dict[str, Organization]:
    return {"ORG-DEMO": Organization(id="ORG-DEMO", name="Demo Lending Co")}


@lru_cache
def get_organization_repository() -> OrganizationRepository:
    """Return the configured repository (Supabase if set, else in-memory)."""
    settings: Settings = get_settings()
    if settings.supabase_url and settings.supabase_key:
        from vera.repositories.supabase_repo import build_client

        return SupabaseOrganizationRepository(
            build_client(settings), settings.organizations_table
        )
    return InMemoryOrganizationRepository(demo_organizations())
