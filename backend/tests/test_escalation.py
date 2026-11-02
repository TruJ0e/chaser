from app.escalation import choose_stage
from app.models import Invoice


def invoice(days: int, amount: float) -> Invoice:
    return Invoice(id="i", number="n", customer_name="c", customer_email="c@example.com", amount=amount, status="SENT", due_date="2026-01-01", days_overdue=days, payment_link="https://example.com")


def test_standard_ladder():
    assert choose_stage(invoice(3, 500))[0] == "nudge"
    assert choose_stage(invoice(20, 500))[0] == "reminder"
    assert choose_stage(invoice(50, 500))[0] == "final"


def test_balance_risk_accelerates_stage():
    assert choose_stage(invoice(8, 5_000))[0] == "reminder"
    assert choose_stage(invoice(31, 10_000))[0] == "final"
