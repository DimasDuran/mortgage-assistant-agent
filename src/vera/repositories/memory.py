"""In-memory application repository (for development and tests)."""

from vera.domain.models import (
    Address,
    Application,
    BorrowerInformation,
    Employment,
    FinancialProfile,
    GrossMonthlyIncome,
    Income,
    Liability,
    LoanAndProperty,
    Name,
    SubjectProperty,
)
from vera.repositories.base import ApplicationRepository, PaginatedResult


class InMemoryApplicationRepository(ApplicationRepository):
    """Keeps applications in a dict. Lost on restart; not for production."""

    def __init__(self, seed: dict[str, Application] | None = None) -> None:
        self._store: dict[str, Application] = dict(seed or {})

    def get(self, application_id: str) -> Application | None:
        return self._store.get(application_id)

    def upsert(self, application: Application) -> None:
        self._store[application.id] = application

    def list(
        self,
        organization_id: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> PaginatedResult:
        items = list(self._store.values())
        if organization_id is not None:
            items = [a for a in items if a.organization_id == organization_id]
        total = len(items)
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return PaginatedResult(items=items, total=total)


def demo_applications() -> dict[str, Application]:
    """Sample applications used in development and to seed Supabase."""
    return {
        "APP-1001": Application(
            id="APP-1001",
            organization_id="ORG-DEMO",
            status="under_review",
            borrower=BorrowerInformation(name=Name(first="Ana", last="Ramirez")),
            income=Income(
                employments=[
                    Employment(
                        employer_name="Acme Corp",
                        income=GrossMonthlyIncome(base=25_000),
                    )
                ]
            ),
            financial_profile=FinancialProfile(
                liabilities=[
                    Liability(
                        liability_type="installment",
                        company_name="Auto Finance Co",
                        monthly_payment=600,
                        unpaid_balance=18_000,
                    )
                ]
            ),
            loan_property=LoanAndProperty(
                subject_property=SubjectProperty(
                    loan_amount=1_600_000,
                    loan_purpose="purchase",
                    property_address=Address(
                        street="1234 Johnson Street",
                        city="San Francisco",
                        state="CA",
                        postal_code="94182",
                    ),
                    property_value=2_000_000,
                    occupancy_type="primary_residence",
                )
            ),
        ),
        "APP-1002": Application(
            id="APP-1002",
            organization_id="ORG-DEMO",
            status="in_progress",
            borrower=BorrowerInformation(name=Name(first="Luis", last="Soto")),
            loan_property=LoanAndProperty(
                subject_property=SubjectProperty(
                    loan_amount=300_000,
                    loan_purpose="rate_term_refinance",
                    property_address=Address(
                        street="55 Oak Ave",
                        city="Austin",
                        state="TX",
                        postal_code="78701",
                    ),
                    property_value=320_000,
                    occupancy_type="primary_residence",
                )
            ),
        ),
    }
