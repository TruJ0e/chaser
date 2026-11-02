from __future__ import annotations

from datetime import date, timedelta

from .models import Invoice


def _due(days_overdue: int) -> str:
    # Keep the demo realistic whatever day it is run.
    return (date.today() - timedelta(days=days_overdue)).isoformat()


MOCK_INVOICES = [
    Invoice(id="INV2-DEMO-1001", number="INV-1001", customer_name="Northstar Studio", customer_email="ap@northstar.example", amount=850.00, status="SENT", due_date=_due(6), days_overdue=6, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1001", history_note="Usually pays within ten days; prefers concise messages."),
    Invoice(id="INV2-DEMO-1002", number="INV-1002", customer_name="Juniper & Co.", customer_email="mira@juniper.example", amount=4250.00, status="SENT", due_date=_due(18), days_overdue=18, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1002", history_note="Long-term client with a strong payment history."),
    Invoice(id="INV2-DEMO-1003", number="INV-1003", customer_name="Beacon Works", customer_email="billing@beacon.example", amount=12800.00, status="SENT", due_date=_due(35), days_overdue=35, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1003", history_note="Two previous reminders received no response."),
    Invoice(id="INV2-DEMO-1004", number="INV-1004", customer_name="Cedar House", customer_email="hello@cedarhouse.example", amount=1200.00, status="SENT", due_date=_due(47), days_overdue=47, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1004", history_note="No disputes are recorded for this invoice."),
    Invoice(id="INV2-DEMO-1005", number="INV-1005", customer_name="Atlas Field Labs", customer_email="finance@atlasfield.example", amount=7600.00, status="SENT", due_date=_due(10), days_overdue=10, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1005", history_note="High-value account; keep communication professional."),
    Invoice(id="INV2-DEMO-1006", number="INV-1006", customer_name="Common Thread", customer_email="owner@commonthread.example", amount=325.00, status="SENT", due_date=_due(2), days_overdue=2, payment_link="https://www.sandbox.paypal.com/invoice/p/#INV2-DEMO-1006", history_note="First invoice for this customer."),
]
