"""API tests with a fake agent (no model, no network)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from vera.api import app, get_agent, get_repo
from vera.core.config import get_settings
from vera.repositories.memory import InMemoryApplicationRepository


class _FakeAgent:
    """Stands in for the compiled agent; returns a fixed reply."""

    async def ainvoke(self, payload: Any, config: Any) -> dict[str, Any]:
        return {"messages": [AIMessage(content="Test reply.")]}


def _client() -> TestClient:
    app.dependency_overrides[get_agent] = lambda: _FakeAgent()
    return TestClient(app)


def test_health():
    assert _client().get("/health").json() == {"status": "ok"}


def test_chat_returns_reply():
    response = _client().post("/chat", json={"message": "hi", "thread_id": "t1"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Test reply."


def test_chat_requires_api_key_when_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VERA_API_KEY", "secret-123")
    get_settings.cache_clear()
    client = _client()
    try:
        without = client.post("/chat", json={"message": "hi", "thread_id": "t1"})
        assert without.status_code == 401

        with_key = client.post(
            "/chat",
            json={"message": "hi", "thread_id": "t1"},
            headers={"x-api-key": "secret-123"},
        )
        assert with_key.status_code == 200
    finally:
        get_settings.cache_clear()
        app.dependency_overrides.clear()


def _client_with_repo() -> TestClient:
    repo = InMemoryApplicationRepository()  # one shared instance across requests
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


def test_create_and_get_application():
    client = _client_with_repo()
    try:
        created = client.post(
            "/applications", json={"name": "Ana case", "organization_id": "ORG-DEMO"}
        ).json()
        app_id = created["id"]
        assert created["status"] == "draft"
        assert created["organization_id"] == "ORG-DEMO"
        got = client.get(f"/applications/{app_id}")
        assert got.status_code == 200
        assert got.json()["name"] == "Ana case"
    finally:
        app.dependency_overrides.clear()


def test_put_borrower_and_missing_returns_404():
    client = _client_with_repo()
    try:
        app_id = client.post(
            "/applications", json={"name": "c", "organization_id": "ORG-DEMO"}
        ).json()["id"]
        ok = client.put(
            f"/applications/{app_id}/borrower", json={"name": {"first": "Ana"}}
        )
        assert ok.status_code == 200
        assert ok.json()["borrower"]["name"]["first"] == "Ana"

        missing = client.put(
            "/applications/NOPE/borrower", json={"name": {"first": "X"}}
        )
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
