"""Invite a person via Supabase Auth (invite-only account creation).

Supabase emails the invitee a link to set their password. We attach the app
role, the tenant (org_id) and, for borrowers, the case id as user_metadata so
the token they later receive is already scoped. Building the admin client
requires the service role key.
"""

from collections.abc import Callable

from vera.core.config import Settings
from vera.domain.enums import UserRole

# (email, role, org_id, application_id) -> None. application_id is None for staff
# invites (they are not tied to one case). Injected as a dependency so the API
# can be tested with a fake that records calls instead of hitting Supabase.
Inviter = Callable[[str, UserRole, str, str | None], None]


def build_supabase_inviter(settings: Settings) -> Inviter:
    """Return an inviter backed by the Supabase admin API.

    The client is built lazily on first call so that resolving this as a
    dependency never fails: authorization (who may invite) is checked first,
    and a missing Supabase config only surfaces when an invite is truly sent.
    """

    def invite(
        email: str, role: UserRole, org_id: str, application_id: str | None
    ) -> None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("Supabase is not configured; cannot send invitations.")

        from supabase_auth.types import InviteUserByEmailOptions

        from supabase import create_client

        client = create_client(settings.supabase_url, settings.supabase_key)
        data: dict[str, object] = {"role": role, "org_id": org_id}
        if application_id is not None:
            data["application_id"] = application_id
        options: InviteUserByEmailOptions = {"data": data}
        if settings.auth_redirect_url:
            options["redirect_to"] = settings.auth_redirect_url
        client.auth.admin.invite_user_by_email(email, options)

    return invite
