from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .activity_log import ActivityLog
from .ai_client import AIClient, AIClientError
from .config import settings
from .escalation import choose_stage
from .models import ActivityEvent, DraftRequest, DraftResult, Invoice
from .paypal_client import OPEN_STATUSES, PayPalClient, PayPalError


app = FastAPI(title="Chaser API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

paypal = PayPalClient()
ai = AIClient()
activity = ActivityLog(settings.activity_log)


def _paypal_to_invoice(payload: dict[str, Any]) -> Invoice:
    if "days_overdue" in payload:
        return Invoice.model_validate(payload)
    detail = payload.get("detail", {})
    recipients = payload.get("primary_recipients", [])
    billing = recipients[0].get("billing_info", {}) if recipients else {}
    name = billing.get("name", {})
    customer_name = billing.get("business_name") or " ".join(
        part for part in [name.get("given_name"), name.get("surname")] if part
    ) or billing.get("email_address", "Customer")
    due_date = detail.get("payment_term", {}).get("due_date") or detail.get("invoice_date") or date.today().isoformat()
    try:
        overdue = max((date.today() - date.fromisoformat(due_date[:10])).days, 0)
    except ValueError:
        overdue = 0
    # Chase the outstanding balance, not the invoice total (partial payments).
    amount = payload.get("due_amount") or payload.get("amount", {})
    payment_link = detail.get("metadata", {}).get("recipient_view_url") or next(
        (link.get("href", "") for link in payload.get("links", []) if link.get("rel") in {"payer-view", "pay"}),
        "",
    )
    return Invoice(
        id=payload["id"],
        number=detail.get("invoice_number", payload["id"]),
        customer_name=customer_name,
        customer_email=billing.get("email_address", ""),
        amount=float(amount.get("value", 0)),
        currency=amount.get("currency_code", "USD"),
        status=payload.get("status", "UNKNOWN"),
        due_date=due_date[:10],
        days_overdue=overdue,
        payment_link=payment_link,
        history_note="PayPal invoice; relationship history is not available yet.",
    )


async def _invoices() -> list[Invoice]:
    listing = await paypal.search_invoices(due_before=date.today().isoformat())
    if paypal.mock_mode:
        return [Invoice.model_validate(item) for item in listing["items"]]
    invoices: list[Invoice] = []
    for summary in listing.get("items", []):
        if summary.get("status") not in OPEN_STATUSES:
            continue
        details = await paypal.get_invoice(summary["id"])
        invoice = _paypal_to_invoice(details)
        if invoice.days_overdue > 0:
            invoices.append(invoice)
    return invoices


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "paypal_mode": "mock" if paypal.mock_mode else ("sandbox" if paypal.sandbox else "live"),
        "ai_mode": "mock" if ai.mock_mode else "nebius",
        "sending_enabled": False,
    }


@app.get("/api/invoices", response_model=list[Invoice])
async def list_invoices() -> list[Invoice]:
    try:
        return await _invoices()
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/invoices/{invoice_id}/draft", response_model=DraftResult)
async def create_draft(invoice_id: str, request: DraftRequest) -> DraftResult:
    try:
        invoice = next((item for item in await _invoices() if item.id == invoice_id), None)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    stage, rationale = choose_stage(invoice)
    try:
        subject, body, generated_by = await ai.draft(invoice, stage, rationale, request.context)
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    result = DraftResult(
        invoice_id=invoice.id,
        stage=stage,
        subject=subject,
        body=body,
        rationale=rationale,
        generated_by=generated_by,
    )
    activity.append(
        ActivityEvent(
            timestamp=datetime.now(UTC),
            invoice_id=invoice.id,
            invoice_number=invoice.number,
            stage=stage,
            tone_rationale=rationale,
            generated_by=generated_by,
        )
    )
    return result


@app.get("/api/activity")
async def list_activity(limit: int = 50) -> list[dict]:
    return activity.read(max(1, min(limit, 200)))
