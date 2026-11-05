from __future__ import annotations

import time
from datetime import date
from typing import Any, Protocol, runtime_checkable

import httpx

from .config import Settings, settings
from .mock_data import MOCK_INVOICES, MOCK_RECOVERED_PAYMENTS


OPEN_STATUSES = ("SENT", "UNPAID", "PARTIALLY_PAID")


class PayPalError(RuntimeError):
    pass


@runtime_checkable
class PayPalClient(Protocol):
    """The integration seam consumed by the Chaser application."""

    mode: str

    async def list_invoices(
        self, page: int = 1, page_size: int = 100, total_required: bool = True
    ) -> dict[str, Any]: ...

    async def search_invoices(
        self,
        statuses: tuple[str, ...] = OPEN_STATUSES,
        *,
        due_before: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]: ...

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]: ...

    async def recovered_revenue(self, since: date) -> float: ...

    async def send_reminder(
        self,
        invoice_id: str,
        *,
        subject: str | None = None,
        note: str | None = None,
        send_to_invoicer: bool = False,
    ) -> None: ...


class MockPayPalClient:
    """Deterministic, network-free PayPal adapter used by the demo."""

    mode = "mock"

    async def list_invoices(
        self, page: int = 1, page_size: int = 100, total_required: bool = True
    ) -> dict[str, Any]:
        del page, page_size, total_required
        return {
            "total_pages": 1,
            "total_items": len(MOCK_INVOICES),
            "items": [invoice.model_dump() for invoice in MOCK_INVOICES],
            "links": [],
            "mock": True,
        }

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        for invoice in MOCK_INVOICES:
            if invoice.id == invoice_id:
                return invoice.model_dump()
        raise PayPalError(f"Mock invoice not found: {invoice_id}")

    async def search_invoices(
        self,
        statuses: tuple[str, ...] = OPEN_STATUSES,
        *,
        due_before: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        del due_before, page, page_size
        items = [
            invoice.model_dump() for invoice in MOCK_INVOICES if invoice.status in statuses
        ]
        return {
            "total_pages": 1,
            "total_items": len(items),
            "items": items,
            "links": [],
            "mock": True,
        }

    async def recovered_revenue(self, since: date) -> float:
        return sum(
            payment["amount"]
            for payment in MOCK_RECOVERED_PAYMENTS
            if payment["paid_at"] >= since
        )

    async def send_reminder(
        self,
        invoice_id: str,
        *,
        subject: str | None = None,
        note: str | None = None,
        send_to_invoicer: bool = False,
    ) -> None:
        del invoice_id, subject, note, send_to_invoicer
        raise PayPalError("Reminder sending is disabled in mock mode")


class PayPalRESTClient:
    """Async PayPal Invoicing API v2 adapter for sandbox or production."""

    def __init__(
        self,
        config: Settings = settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not (config.paypal_client_id and config.paypal_client_secret):
            raise ValueError("PayPalRESTClient requires a client ID and client secret")
        self.client_id = config.paypal_client_id
        self.client_secret = config.paypal_client_secret
        self.sandbox = config.paypal_sandbox
        self.mode = "sandbox" if self.sandbox else "live"
        self.base_url = (
            "https://api-m.sandbox.paypal.com"
            if self.sandbox
            else "https://api-m.paypal.com"
        )
        self._transport = transport
        self._token: str | None = None
        self._token_expires_at = 0.0

    async def _access_token(self) -> str:
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
        response = await self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")
        return response.json()

    async def search_invoices(
        self,
        statuses: tuple[str, ...] = OPEN_STATUSES,
        *,
        due_before: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"status": list(statuses)[:5]}
        if due_before:
            body["due_date_range"] = {"start": "2000-01-01", "end": due_before}
        response = await self._request(
            "POST",
            "/v2/invoicing/search-invoices",
            params={"page": page, "page_size": page_size, "total_required": "true"},
            json=body,
        )
        return response.json()

    async def recovered_revenue(self, since: date) -> float:
        """Sum paid PayPal invoices dated in the requested reporting period."""
        listing = await self.list_invoices()
        total = 0.0
        for summary in listing.get("items", []):
            if summary.get("status") != "PAID":
                continue
            detail = summary.get("detail", {})
            invoice_date = detail.get("invoice_date", "")[:10]
            try:
                if invoice_date and date.fromisoformat(invoice_date) < since:
                    continue
            except ValueError:
                continue
            amount = summary.get("amount", {})
            total += float(amount.get("value", 0))
        return total

    async def send_reminder(
        self,
        invoice_id: str,
        *,
        subject: str | None = None,
        note: str | None = None,
        send_to_invoicer: bool = False,
    ) -> None:
        body: dict[str, Any] = {
            "send_to_recipient": True,
            "send_to_invoicer": send_to_invoicer,
        }
        if subject:
            body["subject"] = subject
        if note:
            body["note"] = note
        await self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            json=body,
        )


def create_paypal_client(
    config: Settings = settings,
    transport: httpx.AsyncBaseTransport | None = None,
) -> PayPalClient:
    """Select an adapter once at startup; callers stay integration-agnostic."""
    if config.paypal_client_id and config.paypal_client_secret:
        return PayPalRESTClient(config, transport=transport)
    return MockPayPalClient()
