"""Repository contract for applications (the persistence port)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from vera.domain.models import Application


@dataclass
class PaginatedResult:
    items: list[Application]
    total: int


class ApplicationRepository(ABC):
    """Read and write applications. Implementations: in-memory and Supabase."""

    @abstractmethod
    def get(self, application_id: str) -> Application | None:
        """Return the application, or None if it does not exist."""
        ...

    @abstractmethod
    def upsert(self, application: Application) -> None:
        """Create or update the application."""
        ...

    @abstractmethod
    def list(
        self,
        organization_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> PaginatedResult:
        """Return applications, optionally filtered to one organization (tenant).

        Args:
            organization_id: filter by tenant.
            limit: max items to return (None = return all).
            offset: number of items to skip.
        """
        ...
