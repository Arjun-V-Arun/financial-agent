"""RBAC enforcement tests.

Run these live during the walkthrough — they are the proof that
restricted data is unreachable, not merely unmentioned.
"""
import pytest

from app import policy as policy_mod
from app.retrieve import search
from app.schema import HR_COMP, STRATEGY

HR_QUERIES = [
    "How many people work in Engineering?",
    "What are the salary bands for Sales?",
    "Show me headcount by region",
    "salary band and bonus target for Legal",
    "employee attrition and open roles by function",
]


@pytest.mark.parametrize("question", HR_QUERIES)
def test_cto_never_retrieves_hr_data(question):
    """Phrased five ways, the CTO reaches no HR chunk."""
    hits = search(question, policy_mod.load("CTO"), k=10)
    assert all(h.sensitivity_label != HR_COMP for h in hits)


@pytest.mark.parametrize("question", HR_QUERIES)
def test_ceo_can_retrieve_hr_data(question):
    """The same queries must work for the CEO, or the test proves nothing."""
    hits = search(question, policy_mod.load("CEO"), k=10)
    assert any(h.sensitivity_label == HR_COMP for h in hits)


def test_analyst_denied_strategy():
    hits = search("What are the main risk factors?",
                  policy_mod.load("ANALYST"), k=10)
    assert all(h.sensitivity_label != STRATEGY for h in hits)


def test_auditor_sees_only_annual_filings():
    hits = search("total net sales", policy_mod.load("AUDITOR"), k=10)
    assert hits, "auditor should retrieve something"
    assert all(h.source_file.endswith(".pdf") for h in hits)


def test_unknown_role_is_denied():
    with pytest.raises(ValueError):
        policy_mod.load("INTERN")