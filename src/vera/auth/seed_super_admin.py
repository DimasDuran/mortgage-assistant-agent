"""Bootstrap the platform super_admin (run once, out-of-band).

An invite-only system cannot invite its own first user, so the platform
super_admin is created directly via the Supabase admin API:

    VERA_SUPERADMIN_EMAIL=you@co.com VERA_SUPERADMIN_PASSWORD=... \\
        python -m vera.auth.seed_super_admin

After this, the super_admin creates organizations and invites each org's first
admin through the API; nothing else touches Supabase directly.
"""

import os

from dotenv import load_dotenv

from vera.core.config import get_settings


def main() -> None:
    load_dotenv()
    email = os.environ.get("VERA_SUPERADMIN_EMAIL")
    password = os.environ.get("VERA_SUPERADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("Set VERA_SUPERADMIN_EMAIL and VERA_SUPERADMIN_PASSWORD.")

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_KEY must be set.")

    from supabase_auth.types import AdminUserAttributes

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.supabase_key)
    attributes: AdminUserAttributes = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"role": "super_admin"},
    }
    client.auth.admin.create_user(attributes)
    print(f"Created super_admin {email}.")


if __name__ == "__main__":
    main()
