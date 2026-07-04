"""Domain entities aligned to the URLA / Form 1003 sections.

Sections mirror the borrower-facing application: Borrower Information, Income,
Financial Profile, Loan & Property, and Declarations. Sections are optional on
Application so it can be filled progressively. No framework dependencies.
"""

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

from vera.domain.enums import (
    ApplicationStatus,
    AssetType,
    BankruptcyChapter,
    CitizenshipStatus,
    CreditType,
    Ethnicity,
    GiftAssetType,
    GiftSource,
    HispanicOrigin,
    HousingStatus,
    IntendedOccupancy,
    LiabilityType,
    LienType,
    LoanPurpose,
    MaritalStatus,
    MilitaryServiceStatus,
    MortgageType,
    OccupancyType,
    OtherAssetCreditType,
    OtherIncomeType,
    OtherLiabilityType,
    OwnershipShare,
    PriorPropertyTitleType,
    PropertyStatus,
    Race,
    Sex,
)

_SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")


class Name(BaseModel):
    first: str = Field(min_length=1)
    middle: str | None = None
    last: str | None = None
    suffix: str | None = None

    @property
    def full(self) -> str:
        parts = [self.first, self.middle, self.last, self.suffix]
        return " ".join(p for p in parts if p)


class Address(BaseModel):
    street: str = Field(min_length=1)
    unit: str | None = None
    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    postal_code: str = Field(min_length=3)
    country: str | None = None
    years_at_address: int | None = Field(default=None, ge=0)
    months_at_address: int | None = Field(default=None, ge=0, le=11)
    housing: HousingStatus | None = None
    monthly_housing_expense: float | None = Field(default=None, ge=0)


class Contact(BaseModel):
    home_phone: str | None = None
    cell_phone: str | None = None
    work_phone: str | None = None
    work_phone_ext: str | None = None
    email: str | None = None


# --- Section 1a: Borrower Information ---
class BorrowerInformation(BaseModel):
    name: Name
    alternate_names: list[str] = Field(default_factory=list)
    # Sensitive: never echo in chat; captured only via the secure form/API.
    ssn: str | None = Field(default=None)
    date_of_birth: date | None = None
    citizenship: CitizenshipStatus | None = None
    credit_type: CreditType | None = None
    total_borrowers: int | None = Field(default=None, ge=1)
    marital_status: MaritalStatus | None = None
    dependents_number: int = Field(default=0, ge=0)
    dependents_ages: list[int] = Field(default_factory=list)
    contact: Contact | None = None
    current_address: Address | None = None
    former_address: Address | None = None
    mailing_address: Address | None = None

    @property
    def full_name(self) -> str:
        return self.name.full

    @field_validator("ssn")
    @classmethod
    def _ssn_format(cls, value: str | None) -> str | None:
        if value is not None and not _SSN_RE.match(value):
            raise ValueError("ssn must be formatted as 123-45-6789")
        return value


# --- Section 1b: Gross monthly income breakdown ---
class GrossMonthlyIncome(BaseModel):
    base: float = Field(default=0, ge=0)
    overtime: float = Field(default=0, ge=0)
    bonus: float = Field(default=0, ge=0)
    commission: float = Field(default=0, ge=0)
    military_entitlements: float = Field(default=0, ge=0)
    other: float = Field(default=0, ge=0)

    @property
    def total(self) -> float:
        return round(
            self.base
            + self.overtime
            + self.bonus
            + self.commission
            + self.military_entitlements
            + self.other,
            2,
        )


class Employment(BaseModel):
    employer_name: str = Field(min_length=1)
    employer_address: Address | None = None
    employer_phone: str | None = None
    position: str | None = None
    is_business_owner_or_self_employed: bool = False
    ownership_share: OwnershipShare | None = None
    employed_by_party_to_transaction: bool = False
    years_in_line_of_work: int | None = Field(default=None, ge=0)
    months_in_line_of_work: int | None = Field(default=None, ge=0, le=11)
    income: GrossMonthlyIncome = Field(default_factory=GrossMonthlyIncome)
    start_date: date | None = None
    end_date: date | None = None  # set for previous employment
    is_current: bool = True

    @property
    def monthly_income(self) -> float:
        return self.income.total


class OtherIncome(BaseModel):
    income_type: OtherIncomeType
    monthly_amount: float = Field(ge=0)


class Income(BaseModel):
    employments: list[Employment] = Field(default_factory=list)
    other_income: list[OtherIncome] = Field(default_factory=list)

    @property
    def total_monthly_income(self) -> float:
        employed = sum(e.income.total for e in self.employments)
        other = sum(o.monthly_amount for o in self.other_income)
        return round(employed + other, 2)


# --- Section 2: Assets and Liabilities ---
class Asset(BaseModel):
    asset_type: AssetType
    financial_institution: str | None = None
    account_number: str | None = None
    value: float = Field(ge=0)


class OtherAssetCredit(BaseModel):
    credit_type: OtherAssetCreditType
    value: float = Field(ge=0)


class Liability(BaseModel):
    liability_type: LiabilityType
    company_name: str | None = None
    account_number: str | None = None
    unpaid_balance: float = Field(default=0, ge=0)
    to_be_paid_off: bool = False
    monthly_payment: float = Field(ge=0)


class OtherLiability(BaseModel):
    liability_type: OtherLiabilityType
    monthly_payment: float = Field(ge=0)


# --- Section 3: Real Estate owned ---
class PropertyMortgage(BaseModel):
    creditor_name: str | None = None
    account_number: str | None = None
    monthly_payment: float = Field(default=0, ge=0)
    unpaid_balance: float = Field(default=0, ge=0)
    to_be_paid_off: bool = False
    mortgage_type: MortgageType | None = None
    credit_limit: float | None = Field(default=None, ge=0)


class RealEstateOwned(BaseModel):
    address: Address
    property_value: float = Field(ge=0)
    status: PropertyStatus | None = None
    intended_occupancy: IntendedOccupancy | None = None
    monthly_insurance_taxes_dues: float = Field(default=0, ge=0)
    monthly_rental_income: float = Field(default=0, ge=0)
    mortgages: list[PropertyMortgage] = Field(default_factory=list)


class FinancialProfile(BaseModel):
    assets: list[Asset] = Field(default_factory=list)
    other_assets_credits: list[OtherAssetCredit] = Field(default_factory=list)
    liabilities: list[Liability] = Field(default_factory=list)
    other_liabilities: list[OtherLiability] = Field(default_factory=list)
    real_estate: list[RealEstateOwned] = Field(default_factory=list)

    @property
    def total_assets(self) -> float:
        assets = sum(a.value for a in self.assets)
        credits = sum(c.value for c in self.other_assets_credits)
        return round(assets + credits, 2)

    @property
    def total_monthly_debt(self) -> float:
        liabilities = sum(item.monthly_payment for item in self.liabilities)
        other = sum(item.monthly_payment for item in self.other_liabilities)
        return round(liabilities + other, 2)


# --- Section 4: Loan and Property ---
class SubjectProperty(BaseModel):
    loan_amount: float = Field(gt=0)
    loan_purpose: LoanPurpose
    property_address: Address
    county: str | None = None
    number_of_units: int | None = Field(default=None, ge=1)
    property_value: float = Field(gt=0)
    occupancy_type: OccupancyType
    mixed_use: bool = False
    manufactured_home: bool = False

    @property
    def ltv_pct(self) -> float:
        return round(self.loan_amount / self.property_value * 100, 2)


class OtherNewMortgage(BaseModel):
    creditor_name: str | None = None
    lien_type: LienType | None = None
    monthly_payment: float = Field(default=0, ge=0)
    loan_amount: float = Field(default=0, ge=0)
    credit_limit: float | None = Field(default=None, ge=0)


class GiftOrGrant(BaseModel):
    asset_type: GiftAssetType
    source: GiftSource
    deposited: bool = False
    value: float = Field(ge=0)


class LoanAndProperty(BaseModel):
    subject_property: SubjectProperty
    other_new_mortgages: list[OtherNewMortgage] = Field(default_factory=list)
    expected_monthly_rental_income: float | None = Field(default=None, ge=0)
    gifts_or_grants: list[GiftOrGrant] = Field(default_factory=list)


# --- Section 5-6: Declarations and Agreements ---
class Declarations(BaseModel):
    # 5a - About this property and your money for this loan
    will_occupy_as_primary_residence: bool | None = None  # A
    had_ownership_interest_past_three_years: bool | None = None  # A follow-up
    prior_property_type: IntendedOccupancy | None = None  # A: PR/SH/IP
    prior_property_title_type: PriorPropertyTitleType | None = None  # A: how held
    family_or_business_relationship_with_seller: bool | None = None  # B
    borrowing_undisclosed_money: bool | None = None  # C
    undisclosed_borrowed_amount: float | None = Field(default=None, ge=0)  # C
    applying_for_other_mortgage: bool | None = None  # D1
    applying_for_new_credit: bool | None = None  # D2
    property_subject_to_priority_lien: bool | None = None  # E (PACE)

    # 5b - About your finances
    cosigner_or_guarantor_on_undisclosed_debt: bool | None = None  # F
    outstanding_judgments: bool | None = None  # G
    delinquent_or_default_on_federal_debt: bool | None = None  # H
    party_to_lawsuit_with_financial_liability: bool | None = None  # I
    conveyed_title_in_lieu_of_foreclosure: bool | None = None  # J
    completed_preforeclosure_or_short_sale: bool | None = None  # K
    property_foreclosed_past_seven_years: bool | None = None  # L
    declared_bankruptcy_past_seven_years: bool | None = None  # M
    bankruptcy_chapters: list[BankruptcyChapter] = Field(default_factory=list)  # M

    agreed_to_terms: bool = False


# --- Section 7: Military Service ---
class MilitaryService(BaseModel):
    served_in_armed_forces: bool | None = None
    status: list[MilitaryServiceStatus] = Field(default_factory=list)
    active_duty_expiration_date: date | None = None


# --- Section 8: Demographic Information (HMDA) ---
# Ethnicity, sex, and race are multi-select per federal HMDA reporting rules.
class DemographicInformation(BaseModel):
    ethnicity: list[Ethnicity] = Field(default_factory=list)
    hispanic_origins: list[HispanicOrigin] = Field(default_factory=list)
    hispanic_origin_other: str | None = None
    sex: list[Sex] = Field(default_factory=list)
    race: list[Race] = Field(default_factory=list)
    american_indian_tribe: str | None = None
    asian_races: list[str] = Field(default_factory=list)
    pacific_islander_races: list[str] = Field(default_factory=list)


# --- Additional borrowers ---
# Each borrower has their own Section 1 (info + income), 5, 7, and 8. The
# primary borrower lives on the flat Application fields; co-borrowers are
# modeled here so a joint application can carry any number of them.
class Borrower(BaseModel):
    information: BorrowerInformation
    income: Income = Field(default_factory=Income)
    declarations: Declarations | None = None
    military_service: MilitaryService | None = None
    demographic_information: DemographicInformation | None = None


# --- Section 9: Loan Originator Information ---
class LoanOriginator(BaseModel):
    organization_name: str | None = None
    organization_address: Address | None = None
    organization_nmlsr_id: str | None = None
    organization_state_license_id: str | None = None
    originator_name: Name | None = None
    originator_nmlsr_id: str | None = None
    originator_state_license_id: str | None = None
    originator_email: str | None = None
    originator_phone: str | None = None


# --- Top-of-form lender identifiers ---
class LenderIdentifiers(BaseModel):
    agency_case_number: str | None = None
    lender_case_number: str | None = None
    universal_loan_identifier: str | None = None


# --- Organization (tenant): the lender that owns cases and staff ---
class Organization(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


# --- The application: ties the sections together ---
class Application(BaseModel):
    id: str = Field(min_length=1)
    # The tenant that owns this case. None only for legacy/dev data.
    organization_id: str | None = None
    # Human-friendly label for the case (e.g. "Ana - home purchase").
    name: str | None = None
    status: ApplicationStatus = "draft"
    borrower: BorrowerInformation | None = None
    income: Income | None = None
    co_borrowers: list[Borrower] = Field(default_factory=list)
    financial_profile: FinancialProfile | None = None
    loan_property: LoanAndProperty | None = None
    declarations: Declarations | None = None
    military_service: MilitaryService | None = None
    demographic_information: DemographicInformation | None = None
    loan_originator: LoanOriginator | None = None
    lender_identifiers: LenderIdentifiers | None = None

    @property
    def ltv_pct(self) -> float | None:
        if self.loan_property is None:
            return None
        return self.loan_property.subject_property.ltv_pct

    @property
    def combined_monthly_income(self) -> float:
        total = self.income.total_monthly_income if self.income else 0.0
        total += sum(b.income.total_monthly_income for b in self.co_borrowers)
        return round(total, 2)

    @property
    def dti_pct(self) -> float | None:
        # DTI qualifies the whole household, so co-borrower income counts.
        if self.financial_profile is None:
            return None
        income = self.combined_monthly_income
        if income <= 0:
            return None
        return round(self.financial_profile.total_monthly_debt / income * 100, 2)
