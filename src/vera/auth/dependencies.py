"""FastAPI dependencies for authentication and authorization.

The backend talks to Supabase with the service role key (which bypasses RLS),
so authorization is enforced here across two axes: role (who may act) and tenant
(which organization's data they may touch). super_admin is cross-tenant; every
other role is confined to its own organization. RLS on the tables is
defense-in-depth for any direct database access.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from vera.auth.tokens import AuthenticatedUser, AuthError, verify_token
from vera.core.config import get_settings
from vera.domain.enums import UserRole

# When auth is disabled (no JWT secret configured), requests run as this local
# user so development and tests work without tokens. Never rely on this in prod.
# Intentionally NOT super_admin: prevents accidental access to all tenants.
_DEV_USER = AuthenticatedUser(id="dev", role="loan_officer", organization_id="ORG-DEMO")

# Staff can manage cases and invite borrowers; org_admin can also invite staff.
_STAFF_ROLES: frozenset[UserRole] = frozenset(
    {"super_admin", "admin", "loan_officer", "operations"}
)
_ORG_ADMIN_ROLES: frozenset[UserRole] = frozenset({"super_admin", "admin"})


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return authorization[7:]


def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        return _DEV_USER
    try:
        return verify_token(
            _bearer(authorization),
            settings.supabase_jwt_secret,
            settings.supabase_jwt_audience,
        )
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc


UserDep = Annotated[AuthenticatedUser, Depends(require_user)]


def can_access_organization(user: AuthenticatedUser, organization_id: str) -> bool:
    """super_admin reaches any tenant; everyone else only their own."""
    if user.role == "super_admin":
        return True
    return user.organization_id == organization_id


def require_super_admin(user: UserDep) -> AuthenticatedUser:
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Requires the super_admin role.")
    return user


def require_org_admin(user: UserDep) -> AuthenticatedUser:
    """Allow tenant admins (and super_admin) to manage an org's staff."""
    if user.role not in _ORG_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Requires an admin role.")
    return user


def require_staff(user: UserDep) -> AuthenticatedUser:
    """Allow lender-side roles (staff); reject borrowers."""
    if user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Requires a lender-side role.")
    return user
