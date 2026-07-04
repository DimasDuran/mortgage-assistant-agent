"""Repository tests (in-memory; Supabase path needs live credentials)."""

import pytest

from vera.core.config import get_settings
from vera.domain.models import Application
from vera.repositories import get_application_repository
from vera.repositories.memory import InMemoryApplicationRepository, demo_applications


def test_memory_upsert_get_list():
    repo = InMemoryApplicationRepository()
    assert repo.get("X") is None
    repo.upsert(Application(id="X", name="Test case"))
    stored = repo.get("X")
    assert stored is not None
    assert stored.name == "Test case"
    assert len(repo.list().items) == 1


def test_demo_seed_has_cases():
    repo = InMemoryApplicationRepository(demo_applications())
    assert repo.get("APP-1001") is not None
    assert len(repo.list().items) == 2


def test_factory_uses_memory_without_supabase(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    get_application_repository.cache_clear()
    try:
        assert isinstance(get_application_repository(), InMemoryApplicationRepository)
    finally:
        get_application_repository.cache_clear()
