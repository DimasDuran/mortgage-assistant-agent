"""Supabase-backed application repository.

Stores each application as a row in the `applications` table: id, status and the
full application as JSONB (`data`). See supabase/schema.sql for the table.

Sensitive fields (SSN, account numbers) are encrypted at the repository layer
before storage when VERA_ENCRYPTION_KEY is configured.
"""

from copy import deepcopy
from typing import Any, cast

from postgrest.types import CountMethod

from supabase import Client, create_client
from vera.core.config import Settings
from vera.core.encryption import decrypt, encrypt
from vera.domain.models import Application
from vera.repositories.base import ApplicationRepository, PaginatedResult


def _encrypt_account_numbers(fp: dict[str, Any] | None) -> None:
    """Encrypt account numbers in a financial_profile dict, in-place."""
    if not isinstance(fp, dict):
        return
    for asset in fp.get("assets") or []:
        if isinstance(asset, dict) and asset.get("account_number"):
            asset["account_number"] = encrypt(asset["account_number"])
    for liability in fp.get("liabilities") or []:
        if isinstance(liability, dict) and liability.get("account_number"):
            liability["account_number"] = encrypt(liability["account_number"])
    for reo in fp.get("real_estate") or []:
        if isinstance(reo, dict):
            for mtg in reo.get("mortgages") or []:
                if isinstance(mtg, dict) and mtg.get("account_number"):
                    mtg["account_number"] = encrypt(mtg["account_number"])


def _decrypt_account_numbers(fp: dict[str, Any] | None) -> None:
    """Decrypt account numbers in a financial_profile dict, in-place."""
    if not isinstance(fp, dict):
        return
    for asset in fp.get("assets") or []:
        if isinstance(asset, dict) and asset.get("account_number"):
            asset["account_number"] = decrypt(asset["account_number"])
    for liability in fp.get("liabilities") or []:
        if isinstance(liability, dict) and liability.get("account_number"):
            liability["account_number"] = decrypt(liability["account_number"])
    for reo in fp.get("real_estate") or []:
        if isinstance(reo, dict):
            for mtg in reo.get("mortgages") or []:
                if isinstance(mtg, dict) and mtg.get("account_number"):
                    mtg["account_number"] = decrypt(mtg["account_number"])


def _encrypt_borrower_sensitive(borrower: dict[str, Any] | None) -> None:
    """Encrypt SSN and account numbers in a borrower dict, in-place."""
    if not isinstance(borrower, dict):
        return
    if borrower.get("ssn"):
        borrower["ssn"] = encrypt(borrower["ssn"])
    _encrypt_account_numbers(borrower.get("financial_profile"))


def _decrypt_borrower_sensitive(borrower: dict[str, Any] | None) -> None:
    """Decrypt SSN and account numbers in a borrower dict, in-place."""
    if not isinstance(borrower, dict):
        return
    if borrower.get("ssn"):
        borrower["ssn"] = decrypt(borrower["ssn"])
    _decrypt_account_numbers(borrower.get("financial_profile"))


def _encrypt_data(data: dict[str, Any]) -> dict[str, Any]:
    """Encrypt sensitive fields in the application data dict."""
    result = deepcopy(data)
    _encrypt_borrower_sensitive(result.get("borrower"))
    _encrypt_account_numbers(result.get("financial_profile"))
    for cb in result.get("co_borrowers") or []:
        if isinstance(cb, dict):
            _encrypt_borrower_sensitive(cb.get("information"))
            _encrypt_account_numbers(cb.get("financial_profile"))
    return result


def _decrypt_data(data: dict[str, Any]) -> dict[str, Any]:
    """Decrypt sensitive fields in the application data dict."""
    result = deepcopy(data)
    _decrypt_borrower_sensitive(result.get("borrower"))
    _decrypt_account_numbers(result.get("financial_profile"))
    for cb in result.get("co_borrowers") or []:
        if isinstance(cb, dict):
            _decrypt_borrower_sensitive(cb.get("information"))
            _decrypt_account_numbers(cb.get("financial_profile"))
    return result


class SupabaseApplicationRepository(ApplicationRepository):
    """Read/write applications in Supabase Postgres."""

    def __init__(self, client: Client, table: str) -> None:
        self._client = client
        self._table = table

    def get(self, application_id: str) -> Application | None:
        response = (
            self._client.table(self._table)
            .select("data")
            .eq("id", application_id)
            .limit(1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], response.data)
        if not rows:
            return None
        return Application.model_validate(_decrypt_data(rows[0]["data"]))

    def upsert(self, application: Application) -> None:
        self._client.table(self._table).upsert(
            {
                "id": application.id,
                "organization_id": application.organization_id,
                "status": application.status,
                "data": _encrypt_data(application.model_dump(mode="json")),
            }
        ).execute()

    def list(
        self,
        organization_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> PaginatedResult:
        query = (
            self._client.table(self._table)
            .select("data", count=CountMethod.exact)
            .order("id")
        )
        if organization_id is not None:
            query = query.eq("organization_id", organization_id)
        if limit is not None:
            query = query.range(offset, offset + limit - 1)
        response = query.execute()
        rows = cast(list[dict[str, Any]], response.data)
        total = response.count or len(rows)
        return PaginatedResult(
            items=[
                Application.model_validate(_decrypt_data(row["data"]))
                for row in rows
            ],
            total=total,
        )


def build_client(settings: Settings) -> Client:
    """Create a Supabase client, failing clearly if credentials are missing."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set.")
    return create_client(settings.supabase_url, settings.supabase_key)
