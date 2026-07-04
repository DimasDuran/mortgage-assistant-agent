"""Verify Supabase Auth access tokens (JWT) and extract the authenticated user.

Supabase signs access tokens with the project's JWT secret (HS256). We verify
the signature and expiry locally (fast, no network) and read our app role and
the case the user is scoped to from the token's user_metadata.
"""

from typing import get_args

import jwt
from pydantic import BaseModel

from vera.domain.enums import UserRole

_VALID_ROLES = frozenset(get_args(UserRole))


class AuthError(Exception):
    """Raised when a token is missing, malformed, expired, or wrong-audience."""


class AuthenticatedUser(BaseModel):
    id: str
    email: str | None = None
    role: UserRole = "borrower"
    # The tenant this user belongs to (None only for super_admin).
    organization_id: str | None = None
    # The case this user is scoped to (set for borrower/co_borrower; None for
    # staff, who are not tied to a single application).
    application_id: str | None = None


def verify_token(
    token: str, secret: str, audience: str = "authenticated"
) -> AuthenticatedUser:
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
    except jwt.PyJWTError as exc:
        raise AuthError(str(exc)) from exc

    subject = claims.get("sub")
    if not subject:
        raise AuthError("token has no subject (sub)")

    metadata = claims.get("user_metadata") or {}
    role = metadata.get("role", "borrower")
    if role not in _VALID_ROLES:
        role = "borrower"  # unknown role gets the least privilege

    return AuthenticatedUser(
        id=subject,
        email=claims.get("email"),
        role=role,
        organization_id=metadata.get("org_id"),
        application_id=metadata.get("application_id"),
    )
