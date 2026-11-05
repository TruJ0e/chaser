from __future__ import annotations

from datetime import date, timedelta

from .models import Invoice


MOCK_INVOICES = [
    Invoice(id="INV2-DEMO-1001", number="INV-1001", customer_name="Northstar Studio", customer_email="ap@northstar.example", amount=850.00, status="SENT", due_date=(date.today() - timedelta(days=6)).isoformat(), days_overdue=6, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1001", history_note="Usually pays within ten days; prefers concise messages."),
    Invoice(id="INV2-DEMO-1002", number="INV-1002", customer_name="Juniper & Co.", customer_email="mira@juniper.example", amount=4250.00, status="SENT", due_date=(date.today() - timedelta(days=18)).isoformat(), days_overdue=18, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1002", history_note="Long-term client with a strong payment history."),
    Invoice(id="INV2-DEMO-1003", number="INV-1003", customer_name="Beacon Works", customer_email="billing@beacon.example", amount=12800.00, status="SENT", due_date=(date.today() - timedelta(days=35)).isoformat(), days_overdue=35, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1003", history_note="Two previous reminders received no response."),
    Invoice(id="INV2-DEMO-1004", number="INV-1004", customer_name="Cedar House", customer_email="hello@cedarhouse.example", amount=1200.00, status="SENT", due_date=(date.today() - timedelta(days=47)).isoformat(), days_overdue=47, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1004", history_note="No disputes are recorded for this invoice."),
    Invoice(id="INV2-DEMO-1005", number="INV-1005", customer_name="Atlas Field Labs", customer_email="finance@atlasfield.example", amount=7600.00, status="SENT", due_date=(date.today() - timedelta(days=10)).isoformat(), days_overdue=10, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1005", history_note="High-value account; keep communication professional."),
    Invoice(id="INV2-DEMO-1006", number="INV-1006", customer_name="Common Thread", customer_email="owner@commonthread.example", amount=325.00, status="SENT", due_date=(date.today() - timedelta(days=2)).isoformat(), days_overdue=2, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1006", history_note="First invoice for this customer."),
]


# Paid invoice fixtures power the recovered-revenue KPI without a network call.
MOCK_RECOVERED_PAYMENTS = [
    {"invoice_id": "INV2-PAID-0901", "amount": 8_950.00, "paid_at": date.today().replace(day=1)},
    {"invoice_id": "INV2-PAID-0902", "amount": 5_200.00, "paid_at": date.today().replace(day=2)},
    {"invoice_id": "INV2-PAID-0903", "amount": 4_300.00, "paid_at": date.today().replace(day=3)},
]
