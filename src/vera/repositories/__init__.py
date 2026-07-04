"""Application repository selection.

Use Supabase when its credentials are configured; otherwise an in-memory
repository seeded with demo data (development and tests).
"""

from functools import lru_cache

from vera.core.config import get_settings
from vera.repositories.base import ApplicationRepository
from vera.repositories.memory import InMemoryApplicationRepository, demo_applications


@lru_cache
def get_application_repository() -> ApplicationRepository:
    """Return the configured repository (Supabase if set, else in-memory)."""
    settings = get_settings()
    if settings.supabase_url and settings.supabase_key:
        # Imported lazily so the in-memory path never requires the Supabase client.
        from vera.repositories.supabase_repo import (
            SupabaseApplicationRepository,
            build_client,
        )

        return SupabaseApplicationRepository(
            build_client(settings), settings.supabase_table
        )
    return InMemoryApplicationRepository(demo_applications())
