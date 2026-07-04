"""Unit tests for the deterministic tools (no LLM, no network)."""

import pytest

from vera.repositories.memory import InMemoryApplicationRepository, demo_applications
from vera.tools.applications import make_application_status
from vera.tools.calculations import calculate_dti, calculate_ltv
from vera.tools.escalation import escalate_to_loan_officer


@pytest.fixture
def app_status_tool():
    repo = InMemoryApplicationRepository(demo_applications())
    return make_application_status(repo)


def test_calculate_ltv_basic():
    result = calculate_ltv.invoke({"loan_amount": 800_000, "property_value": 1_000_000})
    assert result["ltv_pct"] == 80.0


def test_calculate_ltv_rejects_non_positive():
    with pytest.raises(ValueError):
        calculate_ltv.invoke({"loan_amount": 0, "property_value": 1_000_000})


def test_calculate_dti_basic():
    result = calculate_dti.invoke({"monthly_income": 10_000, "monthly_debts": 3_000})
    assert result["dti_pct"] == 30.0


def test_application_status_found(app_status_tool):
    result = app_status_tool.invoke({"application_id": "APP-1001"})
    assert result["found"] is True
    assert result["status"] == "under_review"
    assert result["ltv_pct"] == 80.0


def test_application_status_not_found(app_status_tool):
    result = app_status_tool.invoke({"application_id": "NOPE"})
    assert result["found"] is False


def test_escalate_to_loan_officer():
    result = escalate_to_loan_officer.invoke(
        {"reason": "user requested a human", "application_id": "APP-1001"}
    )
    assert result["status"] == "escalated"
    assert result["application_id"] == "APP-1001"
