import asyncio
from pathlib import Path

import httpx

from app.config import Settings
from app.paypal_client import PayPalClient


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
    client = PayPalClient(config, transport=httpx.MockTransport(handler))

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
