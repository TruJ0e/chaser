from __future__ import annotations

import time
from typing import Any

import httpx

from .config import Settings, settings
from .mock_data import MOCK_INVOICES


class PayPalError(RuntimeError):
    pass


class PayPalClient:
    """Small async client for PayPal Invoicing API v2.

    `send_reminder` implements the verified endpoint, but the Chaser API does not
    expose it yet. This prototype is deliberately draft-only.
    """

    def __init__(self, config: Settings = settings, transport: httpx.AsyncBaseTransport | None = None):
        self.client_id = config.paypal_client_id
        self.client_secret = config.paypal_client_secret
        self.sandbox = config.paypal_sandbox
        self.base_url = (
            "https://api-m.sandbox.paypal.com"
            if self.sandbox
            else "https://api-m.paypal.com"
        )
        self.mock_mode = not (self.client_id and self.client_secret)
        self._transport = transport
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _access_token(self) -> str:
        if self.mock_mode:
            raise PayPalError("PayPal credentials are absent; client is in mock mode")
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json"},
                data={"grant_type": "client_credentials"},
            )
        self._raise_for_status(response)
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 300))
        return self._token

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        token = await self._access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
            response = await client.request(
                method, f"{self.base_url}{path}", headers=headers, **kwargs
            )
        self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            debug_id = response.headers.get("paypal-debug-id", "unknown")
            raise PayPalError(
                f"PayPal API returned {response.status_code} (debug id: {debug_id})"
            ) from exc

    async def list_invoices(
        self, page: int = 1, page_size: int = 100, total_required: bool = True
    ) -> dict[str, Any]:
        if self.mock_mode:
            return {
                "total_pages": 1,
                "total_items": len(MOCK_INVOICES),
                "items": [invoice.model_dump() for invoice in MOCK_INVOICES],
                "links": [],
                "mock": True,
            }
        response = await self._request(
            "GET",
            "/v2/invoicing/invoices",
            params={
                "page": page,
                "page_size": page_size,
                "total_required": str(total_required).lower(),
                "fields": "all",
            },
        )
        return response.json()

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        if self.mock_mode:
            for invoice in MOCK_INVOICES:
                if invoice.id == invoice_id:
                    return invoice.model_dump()
            raise PayPalError(f"Mock invoice not found: {invoice_id}")
        response = await self._request(
            "GET", f"/v2/invoicing/invoices/{invoice_id}"
        )
        return response.json()

    async def send_reminder(
        self, invoice_id: str, *, send_to_invoicer: bool = False
    ) -> None:
        """Send PayPal's system reminder. Intentionally unused until send approval exists."""
        if self.mock_mode:
            raise PayPalError("Reminder sending is disabled in mock mode")
        await self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            json={
                "send_to_recipient": True,
                "send_to_invoicer": send_to_invoicer,
            },
        )
