"""Test isolation: tests must not read the developer's .env.

The real .env has Supabase and API keys; without this, tests would hit Supabase
and enforce auth. Here we ignore the .env file and use a controlled environment
so the in-memory repository and no-auth defaults apply.
"""

import pytest

from vera.core import config
from vera.repositories import get_application_repository
from vera.repositories.organizations import get_organization_repository

# api.py calls load_dotenv() at import, which pollutes os.environ with the real
# .env values; clear them so tests use in-memory + no-auth defaults.
_ENV_VARS_TO_CLEAR = (
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_JWT_SECRET",
    "VERA_API_KEY",
    "VOYAGE_API_KEY",
    "PINECONE_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_PROJECT",
    "EMBEDDINGS_PROVIDER",
)


@pytest.fixture(autouse=True)
def _isolate_from_env_file(monkeypatch: pytest.MonkeyPatch):
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(config.Settings.model_config, "env_file", None)
    config.get_settings.cache_clear()
    get_application_repository.cache_clear()
    get_organization_repository.cache_clear()
    yield
    config.get_settings.cache_clear()
    get_application_repository.cache_clear()
    get_organization_repository.cache_clear()
