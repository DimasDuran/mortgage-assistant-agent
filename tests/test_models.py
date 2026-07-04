"""Tests for the URLA-aligned domain models."""

from datetime import date

import pytest
from pydantic import ValidationError

from vera.domain.models import (
    Address,
    Application,
    Asset,
    Borrower,
    BorrowerInformation,
    Declarations,
    DemographicInformation,
    Employment,
    FinancialProfile,
    GiftOrGrant,
    GrossMonthlyIncome,
    Income,
    LenderIdentifiers,
    Liability,
    LoanAndProperty,
    LoanOriginator,
    MilitaryService,
    Name,
    OtherAssetCredit,
    OtherLiability,
    OtherNewMortgage,
    PropertyMortgage,
    RealEstateOwned,
    SubjectProperty,
)


def _address() -> Address:
    return Address(street="1 Main St", city="Austin", state="TX", postal_code="78701")


def test_subject_property_ltv():
    subject = SubjectProperty(
        loan_amount=800_000,
        loan_purpose="purchase",
        property_address=_address(),
        property_value=1_000_000,
        occupancy_type="primary_residence",
    )
    assert subject.ltv_pct == 80.0


def test_income_total():
    income = Income(
        employments=[
            Employment(employer_name="Acme", income=GrossMonthlyIncome(base=8_000))
        ]
    )
    assert income.total_monthly_income == 8_000


def test_application_dti_and_ltv():
    app = Application(
        id="APP-X",
        income=Income(
            employments=[
                Employment(employer_name="Acme", income=GrossMonthlyIncome(base=8_000))
            ]
        ),
        financial_profile=FinancialProfile(
            liabilities=[
                Liability(
                    liability_type="installment",
                    monthly_payment=2_000,
                    unpaid_balance=1,
                )
            ]
        ),
    )
    assert app.dti_pct == 25.0
    assert app.ltv_pct is None  # no loan_property yet

    app.loan_property = LoanAndProperty(
        subject_property=SubjectProperty(
            loan_amount=900_000,
            loan_purpose="purchase",
            property_address=_address(),
            property_value=1_000_000,
            occupancy_type="primary_residence",
        )
    )
    assert app.ltv_pct == 90.0


def test_ssn_format_validation():
    BorrowerInformation(name=Name(first="Ana"), ssn="123-45-6789")  # valid
    with pytest.raises(ValidationError):
        BorrowerInformation(name=Name(first="Ana"), ssn="123456789")


def test_full_name_computed_from_structured_name():
    borrower = BorrowerInformation(name=Name(first="Ana", middle="M", last="Ramirez"))
    assert borrower.full_name == "Ana M Ramirez"


def test_income_breakdown_totals():
    income = GrossMonthlyIncome(base=5_000, overtime=500, bonus=1_000)
    assert income.total == 6_500


def test_real_estate_owned_with_mortgages():
    reo = RealEstateOwned(
        address=_address(),
        property_value=500_000,
        status="retained",
        intended_occupancy="investment_property",
        monthly_rental_income=2_500,
        mortgages=[
            PropertyMortgage(
                creditor_name="Big Bank",
                monthly_payment=1_800,
                unpaid_balance=250_000,
                mortgage_type="conventional",
            )
        ],
    )
    assert reo.mortgages[0].mortgage_type == "conventional"
    assert reo.mortgages[0].to_be_paid_off is False


def test_loan_property_gifts_and_other_mortgages():
    loan_property = LoanAndProperty(
        subject_property=SubjectProperty(
            loan_amount=800_000,
            loan_purpose="purchase",
            property_address=_address(),
            county="Travis",
            number_of_units=1,
            property_value=1_000_000,
            occupancy_type="primary_residence",
        ),
        other_new_mortgages=[
            OtherNewMortgage(
                creditor_name="Second Lender",
                lien_type="subordinate_lien",
                loan_amount=50_000,
                monthly_payment=400,
            )
        ],
        gifts_or_grants=[
            GiftOrGrant(
                asset_type="cash_gift",
                source="relative",
                deposited=True,
                value=20_000,
            )
        ],
    )
    assert loan_property.subject_property.county == "Travis"
    assert loan_property.other_new_mortgages[0].lien_type == "subordinate_lien"
    assert loan_property.gifts_or_grants[0].value == 20_000


def test_declarations_full_fidelity():
    decl = Declarations(
        will_occupy_as_primary_residence=True,
        had_ownership_interest_past_three_years=True,
        prior_property_type="primary_residence",
        prior_property_title_type="joint_with_spouse",
        borrowing_undisclosed_money=True,
        undisclosed_borrowed_amount=10_000,
        applying_for_new_credit=False,
        declared_bankruptcy_past_seven_years=True,
        bankruptcy_chapters=["chapter_7", "chapter_13"],
        agreed_to_terms=True,
    )
    assert decl.prior_property_title_type == "joint_with_spouse"
    assert decl.undisclosed_borrowed_amount == 10_000
    assert "chapter_7" in decl.bankruptcy_chapters


def test_military_and_demographic_on_application():
    app = Application(
        id="APP-MIL",
        military_service=MilitaryService(
            served_in_armed_forces=True,
            status=["active_duty"],
            active_duty_expiration_date=date(2027, 1, 1),
        ),
        demographic_information=DemographicInformation(
            ethnicity=["hispanic_or_latino"],
            hispanic_origins=["mexican"],
            sex=["female"],
            race=["white"],
        ),
    )
    assert app.military_service is not None
    assert app.military_service.status == ["active_duty"]
    assert app.demographic_information is not None
    assert app.demographic_information.ethnicity == ["hispanic_or_latino"]


def test_dti_combines_co_borrower_income():
    app = Application(
        id="APP-JOINT",
        income=Income(
            employments=[
                Employment(employer_name="Acme", income=GrossMonthlyIncome(base=6_000))
            ]
        ),
        co_borrowers=[
            Borrower(
                information=BorrowerInformation(name=Name(first="Sam", last="Lee")),
                income=Income(
                    employments=[
                        Employment(
                            employer_name="Beta",
                            income=GrossMonthlyIncome(base=4_000),
                        )
                    ]
                ),
            )
        ],
        financial_profile=FinancialProfile(
            liabilities=[
                Liability(
                    liability_type="installment",
                    monthly_payment=2_500,
                    unpaid_balance=1,
                )
            ]
        ),
    )
    assert app.combined_monthly_income == 10_000
    assert app.dti_pct == 25.0  # 2500 / 10000


def test_loan_originator_and_lender_identifiers():
    app = Application(
        id="APP-ORIG",
        loan_originator=LoanOriginator(
            organization_name="Vera Lending LLC",
            organization_nmlsr_id="123456",
            originator_name=Name(first="Dana", last="Cruz"),
            originator_nmlsr_id="654321",
            originator_email="dana@example.com",
        ),
        lender_identifiers=LenderIdentifiers(
            agency_case_number="AG-1",
            universal_loan_identifier="ULI-XYZ",
        ),
    )
    assert app.loan_originator is not None
    assert app.loan_originator.organization_nmlsr_id == "123456"
    assert app.lender_identifiers is not None
    assert app.lender_identifiers.universal_loan_identifier == "ULI-XYZ"


def test_financial_profile_totals_include_other():
    profile = FinancialProfile(
        assets=[Asset(asset_type="checking", value=10_000)],
        other_assets_credits=[
            OtherAssetCredit(credit_type="earnest_money", value=5_000)
        ],
        liabilities=[
            Liability(
                liability_type="revolving", monthly_payment=200, unpaid_balance=1_000
            )
        ],
        other_liabilities=[
            OtherLiability(liability_type="child_support", monthly_payment=300)
        ],
    )
    assert profile.total_assets == 15_000
    assert profile.total_monthly_debt == 500
