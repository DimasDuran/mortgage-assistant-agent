"""Closed domain types for the mortgage domain (URLA / Form 1003 aligned)."""

from typing import Literal

# Actor roles for access control. Accounts are provisioned by invitation
# (invite-only, no open signup). Multi-tenant: every role except super_admin is
# scoped to one organization. super_admin is a platform role (creates orgs and
# invites each org's first admin); admin is the tenant admin (invites staff);
# loan_officer/operations are staff; borrower/co_borrower own their case.
UserRole = Literal[
    "super_admin",
    "admin",
    "loan_officer",
    "operations",
    "borrower",
    "co_borrower",
]

# Lifecycle of a case, mirroring the no-account origination flow:
# invitation -> authentication -> dynamic fill -> submit/sign -> automated
# review (with a corrections loop) -> handoff to the loan officer -> decision.
# Allowed transitions live in domain/status.py.
ApplicationStatus = Literal[
    "draft",  # created, before the invitation is sent
    "invited",  # invitation email sent, awaiting authentication
    "in_progress",  # borrower authenticated and filling the form
    "submitted",  # borrower submitted the completed form
    "signed",  # e-signature completed (Section 6, ESIGN)
    "auto_review",  # automated review running (verify docs, cross-check data)
    "corrections_needed",  # review found issues; back to the borrower
    "ready_for_loan_officer",  # clean file, handed off
    "under_review",  # loan officer reviewing
    "approved",  # loan officer approved
    "rejected",  # loan officer rejected
]

# Section 4 - Loan and Property
LoanPurpose = Literal["purchase", "rate_term_refinance", "cash_out_refinance"]
OccupancyType = Literal[
    "primary_residence",
    "second_home",
    "investment_property",
    "fha_secondary_residence",
]

# Section 1a - Borrower Information
CreditType = Literal["individual", "joint"]
MaritalStatus = Literal["married", "separated", "unmarried"]
CitizenshipStatus = Literal[
    "us_citizen",
    "permanent_resident_alien",
    "non_permanent_resident_alien",
]
HousingStatus = Literal["own", "rent", "no_primary_expense"]

# Section 1b - Employment
OwnershipShare = Literal["less_than_25", "25_or_more"]

# Section 1e - Income from other sources (full URLA list)
OtherIncomeType = Literal[
    "alimony",
    "automobile_allowance",
    "boarder_income",
    "capital_gains",
    "child_support",
    "disability",
    "foster_care",
    "housing_or_parsonage",
    "interest_dividends",
    "mortgage_credit_certificate",
    "mortgage_differential",
    "notes_receivable",
    "public_assistance",
    "retirement",
    "royalty_payments",
    "separate_maintenance",
    "social_security",
    "trust",
    "unemployment_benefits",
    "va_compensation",
    "other",
]

# Section 2a - Assets (bank/retirement/other accounts)
AssetType = Literal[
    "checking",
    "savings",
    "money_market",
    "certificate_of_deposit",
    "stock_options",
    "mutual_fund",
    "bonds",
    "stocks",
    "retirement",
    "bridge_loan_proceeds",
    "individual_development_account",
    "trust_account",
    "cash_value_life_insurance",
]

# Section 2b - Other assets and credits
OtherAssetCreditType = Literal[
    "proceeds_from_real_estate_to_be_sold",
    "proceeds_from_non_real_estate_sale",
    "secured_borrowed_funds",
    "unsecured_borrowed_funds",
    "earnest_money",
    "employer_assistance",
    "lot_equity",
    "relocation_funds",
    "rent_credit",
    "sweat_equity",
    "trade_equity",
    "other",
]

# Section 2c - Liabilities
LiabilityType = Literal["revolving", "installment", "open_30_day", "lease", "other"]

# Section 2d - Other liabilities and expenses
OtherLiabilityType = Literal[
    "alimony",
    "child_support",
    "separate_maintenance",
    "job_related_expenses",
    "other",
]

# Section 3 - Real estate owned
PropertyStatus = Literal["sold", "pending_sale", "retained"]
IntendedOccupancy = Literal[
    "primary_residence",
    "second_home",
    "investment_property",
    "other",
]
MortgageType = Literal["fha", "va", "conventional", "usda_rd", "other"]

# Section 4b/4d - additional loan/property details
LienType = Literal["first_lien", "subordinate_lien"]
GiftAssetType = Literal["cash_gift", "gift_of_equity", "grant"]
GiftSource = Literal[
    "community_nonprofit",
    "federal_agency",
    "relative",
    "employer",
    "local_agency",
    "religious_nonprofit",
    "state_agency",
    "unmarried_partner",
    "lender",
    "other",
]

# Section 5 - Declarations
# How the borrower held title to a previously owned property (question 5a.A).
PriorPropertyTitleType = Literal["sole", "joint_with_spouse", "joint_with_other"]
BankruptcyChapter = Literal["chapter_7", "chapter_11", "chapter_12", "chapter_13"]

# Section 7 - Military Service
MilitaryServiceStatus = Literal[
    "active_duty",
    "retired_discharged_separated",
    "reserve_national_guard_non_activated",
    "surviving_spouse",
]

# Section 8 - Demographic Information (HMDA). Multi-select per federal rules.
Ethnicity = Literal["hispanic_or_latino", "not_hispanic_or_latino", "not_provided"]
HispanicOrigin = Literal["mexican", "puerto_rican", "cuban", "other"]
Sex = Literal["female", "male", "not_provided"]
Race = Literal[
    "american_indian_or_alaska_native",
    "asian",
    "black_or_african_american",
    "native_hawaiian_or_other_pacific_islander",
    "white",
    "not_provided",
]
