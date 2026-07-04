"""Auth tests: JWT verification and role/tenant/case-scoped API access."""

import time
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from vera.api import app, get_inviter, get_org_repo, get_repo
from vera.auth.tokens import AuthError, verify_token
from vera.core.config import get_settings
from vera.domain.models import Application, Organization
from vera.repositories.memory import InMemoryApplicationRepository
from vera.repositories.organizations import InMemoryOrganizationRepository

# At least 32 bytes so pyjwt does not warn about a short HMAC key.
_SECRET = "test-jwt-secret-0123456789abcdef-0123456789"


def _token(secret: str = _SECRET, **overrides: Any) -> str:
    payload: dict[str, Any] = {
        "sub": "user-1",
        "aud": "authenticated",
        "email": "a@example.com",
        "exp": int(time.time()) + 3600,
    }
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


def _meta(**kwargs: Any) -> str:
    return _token(user_metadata=kwargs)


# --- Token verification (unit) ---


def test_verify_reads_role_org_and_application():
    token = _meta(role="borrower", org_id="ORG-1", application_id="APP-1")
    user = verify_token(token, _SECRET)
    assert user.id == "user-1"
    assert user.role == "borrower"
    assert user.organization_id == "ORG-1"
    assert user.application_id == "APP-1"


def test_verify_defaults_to_borrower_without_metadata():
    user = verify_token(_token(), _SECRET)
    assert user.role == "borrower"
    assert user.organization_id is None
    assert user.application_id is None


def test_verify_unknown_role_falls_back_to_least_privilege():
    assert verify_token(_meta(role="hacker"), _SECRET).role == "borrower"


def test_verify_rejects_expired_and_wrong_secret():
    with pytest.raises(AuthError):
        verify_token(_token(exp=int(time.time()) - 1), _SECRET)
    with pytest.raises(AuthError):
        verify_token(_token(), "other-secret")


# --- API access control (auth enabled) ---


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _SECRET)
    get_settings.cache_clear()
    repo = InMemoryApplicationRepository(
        {"APP-1": Application(id="APP-1", organization_id="ORG-1")}
    )
    org_repo = InMemoryOrganizationRepository(
        {"ORG-1": Organization(id="ORG-1", name="Org One")}
    )
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_org_repo] = lambda: org_repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def test_missing_token_is_rejected(auth_client: TestClient):
    assert auth_client.get("/applications/APP-1").status_code == 401


def test_borrower_reaches_own_case_only(auth_client: TestClient):
    borrower = _meta(role="borrower", org_id="ORG-1", application_id="APP-1")
    own = auth_client.get("/applications/APP-1", headers=_auth(borrower))
    assert own.status_code == 200
    other = auth_client.get("/applications/APP-OTHER", headers=_auth(borrower))
    assert other.status_code == 404  # does not exist


def test_borrower_cannot_create_or_list(auth_client: TestClient):
    borrower = _meta(role="borrower", org_id="ORG-1", application_id="APP-1")
    assert auth_client.get("/applications", headers=_auth(borrower)).status_code == 403
    created = auth_client.post(
        "/applications", json={"name": "x"}, headers=_auth(borrower)
    )
    assert created.status_code == 403


def test_staff_cannot_reach_other_tenant_case(auth_client: TestClient):
    # A loan officer of ORG-2 must not read ORG-1's case.
    officer = _meta(role="loan_officer", org_id="ORG-2")
    response = auth_client.get("/applications/APP-1", headers=_auth(officer))
    assert response.status_code == 403


def test_officer_can_invite_borrower_to_own_case(auth_client: TestClient):
    sent: list[tuple[str, str, str, str | None]] = []
    app.dependency_overrides[get_inviter] = lambda: (
        lambda email, role, org_id, app_id: sent.append((email, role, org_id, app_id))
    )
    officer = _meta(role="loan_officer", org_id="ORG-1")
    response = auth_client.post(
        "/applications/APP-1/invite",
        json={"email": "b@example.com", "role": "co_borrower"},
        headers=_auth(officer),
    )
    assert response.status_code == 202
    assert sent == [("b@example.com", "co_borrower", "ORG-1", "APP-1")]


def test_borrower_cannot_invite(auth_client: TestClient):
    borrower = _meta(role="borrower", org_id="ORG-1", application_id="APP-1")
    response = auth_client.post(
        "/applications/APP-1/invite",
        json={"email": "b@example.com"},
        headers=_auth(borrower),
    )
    assert response.status_code == 403


def test_only_super_admin_creates_organizations(auth_client: TestClient):
    officer = _meta(role="loan_officer", org_id="ORG-1")
    denied = auth_client.post(
        "/organizations", json={"name": "New Org"}, headers=_auth(officer)
    )
    assert denied.status_code == 403

    superadmin = _meta(role="super_admin")
    created = auth_client.post(
        "/organizations", json={"name": "New Org"}, headers=_auth(superadmin)
    )
    assert created.status_code == 200
    assert created.json()["name"] == "New Org"
    assert created.json()["id"].startswith("ORG-")
