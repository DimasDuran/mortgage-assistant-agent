"""Deterministic mortgage calculation tools.

These run in Python so the numbers are exact; the model must not estimate them.
The docstrings are what the agent reads to decide when to call each tool.
"""

from langchain_core.tools import tool


@tool
def calculate_ltv(loan_amount: float, property_value: float) -> dict[str, object]:
    """Calculate the loan-to-value (LTV) ratio as a percentage.

    Always use this tool for the LTV; never estimate it.

    Args:
        loan_amount: amount to finance (> 0).
        property_value: property price or value (> 0).
    """
    if loan_amount <= 0 or property_value <= 0:
        raise ValueError("loan_amount and property_value must be greater than 0.")
    ltv = loan_amount / property_value * 100
    if ltv <= 80:
        note = "Low LTV; typically avoids private mortgage insurance (PMI)."
    elif ltv <= 95:
        note = "High LTV; likely requires private mortgage insurance (PMI)."
    else:
        note = "Very high LTV (>95%); limited loan options."
    return {"ltv_pct": round(ltv, 2), "note": note}


@tool
def calculate_dti(monthly_income: float, monthly_debts: float) -> dict[str, object]:
    """Calculate the debt-to-income (DTI) ratio as a percentage.

    Always use this tool for the DTI; never estimate it.

    Args:
        monthly_income: gross monthly income (> 0).
        monthly_debts: total monthly debt payments (>= 0).
    """
    if monthly_income <= 0:
        raise ValueError("monthly_income must be greater than 0.")
    if monthly_debts < 0:
        raise ValueError("monthly_debts cannot be negative.")
    dti = monthly_debts / monthly_income * 100
    if dti <= 36:
        note = "Healthy DTI; within typical lender ranges."
    elif dti <= 43:
        note = "Borderline DTI; many programs require <= 43%."
    else:
        note = "High DTI (>43%); approval may be difficult."
    return {"dti_pct": round(dti, 2), "note": note}
