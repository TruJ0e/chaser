from __future__ import annotations

from datetime import date, timedelta

from .models import Invoice


MOCK_INVOICES = [
    Invoice(id="INV2-DEMO-1001", number="INV-1001", business_name="TruJoe Digital", customer_name="Northstar Studio", customer_email="ap@northstar.example", customer_phone="+15550101001", work_reference="website build, October", amount=850.00, status="SENT", due_date=(date.today() - timedelta(days=6)).isoformat(), days_overdue=6, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1001", history_note="We have worked together since 2024; payments are usually prompt, and you prefer concise messages."),
    Invoice(id="INV2-DEMO-1002", number="INV-1002", business_name="TruJoe Digital", customer_name="Juniper & Co.", customer_email="mira@juniper.example", customer_phone="+15550101002", work_reference="monthly website care", amount=4250.00, status="SENT", due_date=(date.today() - timedelta(days=18)).isoformat(), days_overdue=18, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1002", history_note="You have been a client for three years with a consistently strong payment history."),
    Invoice(id="INV2-DEMO-1003", number="INV-1003", business_name="TruJoe Digital", customer_name="Beacon Works", customer_email="billing@beacon.example", customer_phone="+15550101003", work_reference="warehouse brand refresh", amount=12800.00, status="SENT", due_date=(date.today() - timedelta(days=35)).isoformat(), days_overdue=35, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1003", history_note="The launch went smoothly, but our last two invoice notes have not received a reply."),
    Invoice(id="INV2-DEMO-1004", number="INV-1004", business_name="TruJoe Digital", customer_name="Cedar House", customer_email="hello@cedarhouse.example", customer_phone="+15550101004", work_reference="spring campaign landing pages", amount=1200.00, status="SENT", due_date=(date.today() - timedelta(days=47)).isoformat(), days_overdue=47, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1004", history_note="This was our second project together, and the work was approved without revisions."),
    Invoice(id="INV2-DEMO-1005", number="INV-1005", business_name="TruJoe Digital", customer_name="Atlas Field Labs", customer_email="finance@atlasfield.example", customer_phone="+15550101005", work_reference="field research dashboard", amount=7600.00, status="SENT", due_date=(date.today() - timedelta(days=10)).isoformat(), days_overdue=10, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1005", history_note="We support your team each quarter and normally coordinate directly with finance."),
    Invoice(id="INV2-DEMO-1006", number="INV-1006", business_name="TruJoe Digital", customer_name="Common Thread", customer_email="owner@commonthread.example", customer_phone=None, work_reference="product photography session", amount=325.00, status="SENT", due_date=(date.today() - timedelta(days=2)).isoformat(), days_overdue=2, payment_link="http://localhost:8000/mock/pay/INV2-DEMO-1006", history_note="This was our first project together, and the final images were delivered last week."),
]


# Paid invoice fixtures power the recovered-revenue KPI without a network call.
MOCK_RECOVERED_PAYMENTS = [
    {"invoice_id": "INV2-PAID-0901", "amount": 8_950.00, "paid_at": date.today().replace(day=1)},
    {"invoice_id": "INV2-PAID-0902", "amount": 5_200.00, "paid_at": date.today().replace(day=2)},
    {"invoice_id": "INV2-PAID-0903", "amount": 4_300.00, "paid_at": date.today().replace(day=3)},
]
