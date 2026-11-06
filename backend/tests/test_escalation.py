from app.ai_client import AIClient
from app.escalation import choose_channels, choose_stage, render_text
from app.mock_data import MOCK_INVOICES
from app.models import Invoice


def invoice(days: int, amount: float) -> Invoice:
    return Invoice(id="i", number="INV-TEST", business_name="TruJoe Digital", customer_name="c", customer_email="c@example.com", work_reference="test project", amount=amount, status="SENT", due_date="2026-01-01", days_overdue=days, payment_link="https://example.com")


def test_standard_ladder():
    assert choose_stage(invoice(3, 500))[0] == "nudge"
    assert choose_stage(invoice(20, 500))[0] == "reminder"
    assert choose_stage(invoice(50, 500))[0] == "final"


def test_balance_risk_accelerates_stage():
    assert choose_stage(invoice(8, 5_000))[0] == "reminder"
    assert choose_stage(invoice(31, 10_000))[0] == "final"


def test_text_drafts_render_all_stages_under_single_segment_limit():
    item = invoice(3, 500)
    for stage in ("nudge", "reminder", "final"):
        body = render_text(item, stage)
        assert "USD 500.00" in body
        assert item.payment_link in body
        assert len(body) < 160


def test_every_mock_email_and_text_carries_the_relationship():
    banned = ("chaser accounts", "our records show", "final scheduled notice")

    for item in MOCK_INVOICES:
        for stage in ("nudge", "reminder", "final"):
            _, email = AIClient._mock_draft(item, stage)
            text = render_text(item, stage)
            amount = f"{item.currency} {item.amount:,.2f}"
            for draft in (email, text):
                assert item.business_name in draft
                assert item.work_reference in draft
                assert item.number in draft
                assert amount in draft
                assert str(item.days_overdue) in draft
                assert item.payment_link in draft
                assert not any(phrase in draft.lower() for phrase in banned)
            assert len(text) < 160


def test_channel_policy_uses_phone_and_stage():
    item = invoice(3, 500)
    assert choose_channels(item, "nudge")[0] == ["email"]
    item.customer_phone = "+15550100000"
    item.history_note = "Prefers concise messages."
    assert choose_channels(item, "nudge")[0] == ["text"]
    assert choose_channels(item, "reminder")[0] == ["email", "text"]
