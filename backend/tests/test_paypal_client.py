import asyncio
import json
from pathlib import Path

import httpx

from app.config import Settings
from app.paypal_client import MockPayPalClient, PayPalRESTClient, create_paypal_client


def test_verified_v2_paths_and_oauth_flow():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "test-token", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/invoices" and request.method == "GET":
            return httpx.Response(200, json={"items": []})
        if request.url.path == "/v2/invoicing/invoices/INV2-TEST" and request.method == "GET":
            return httpx.Response(200, json={"id": "INV2-TEST"})
        if request.url.path == "/v2/invoicing/invoices/INV2-TEST/remind":
            return httpx.Response(204)
        return httpx.Response(404)

    config = Settings(
        paypal_client_id="client-id",
        paypal_client_secret="client-secret",
        paypal_sandbox=True,
        activity_log=Path("unused.jsonl"),
    )
    client = PayPalRESTClient(config, transport=httpx.MockTransport(handler))

    async def exercise() -> None:
        await client.list_invoices(page=2, page_size=50)
        await client.get_invoice("INV2-TEST")
        await client.send_reminder("INV2-TEST")

    asyncio.run(exercise())

    assert seen[0].url == "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    assert seen[1].url.path == "/v2/invoicing/invoices"
    assert seen[1].url.params["total_required"] == "true"
    assert seen[2].url.path == "/v2/invoicing/invoices/INV2-TEST"
    assert seen[3].url.path == "/v2/invoicing/invoices/INV2-TEST/remind"
    assert seen[3].method == "POST"


def test_factory_keeps_mock_and_rest_adapters_swappable():
    mock = create_paypal_client(Settings(activity_log=Path("unused.jsonl")))
    assert isinstance(mock, MockPayPalClient)
    assert mock.mode == "mock"

    live = create_paypal_client(
        Settings(
            paypal_client_id="client-id",
            paypal_client_secret="client-secret",
            paypal_sandbox=True,
            activity_log=Path("unused.jsonl"),
        )
    )
    assert isinstance(live, PayPalRESTClient)
    assert live.mode == "sandbox"


def test_search_filters_open_statuses_and_remind_body():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "test-token", "expires_in": 3600})
        if request.url.path == "/v2/invoicing/search-invoices":
            return httpx.Response(200, json={"items": []})
        if request.url.path.endswith("/remind"):
            return httpx.Response(204)
        return httpx.Response(404)

    client = PayPalRESTClient(
        Settings(
            paypal_client_id="client-id",
            paypal_client_secret="client-secret",
            paypal_sandbox=True,
            activity_log=Path("unused.jsonl"),
        ),
        transport=httpx.MockTransport(handler),
    )

    async def exercise() -> None:
        await client.search_invoices(due_before="2026-11-02")
        await client.send_reminder("INV2-TEST", subject="Reminder", note="Please pay")

    asyncio.run(exercise())

    search = json.loads(seen[1].content)
    assert search["status"] == ["SENT", "UNPAID", "PARTIALLY_PAID"]
    assert search["due_date_range"]["end"] == "2026-11-02"
    remind = json.loads(seen[2].content)
    assert remind == {
        "send_to_recipient": True,
        "send_to_invoicer": False,
        "subject": "Reminder",
        "note": "Please pay",
    }


def test_normalizer_uses_due_amount_and_recipient_view_url():
    from app.main import _paypal_to_invoice

    invoice = _paypal_to_invoice({
        "id": "INV2-ABCD",
        "status": "PARTIALLY_PAID",
        "detail": {
            "invoice_number": "0042",
            "payment_term": {"due_date": "2000-01-01"},
            "metadata": {
                "recipient_view_url": "https://www.sandbox.paypal.com/invoice/p/#INV2-ABCD"
            },
        },
        "primary_recipients": [{
            "billing_info": {
                "business_name": "Acme",
                "email_address": "ap@acme.example",
            }
        }],
        "amount": {"currency_code": "USD", "value": "100.00"},
        "due_amount": {"currency_code": "USD", "value": "40.00"},
    })
    assert invoice.amount == 40.0
    assert invoice.payment_link.endswith("#INV2-ABCD")
    assert invoice.days_overdue > 0
