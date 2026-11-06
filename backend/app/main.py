from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .activity_log import ActivityLog
from .ai_client import AIClient, AIClientError
from .config import settings
from .escalation import choose_channels, choose_stage, render_text
from .models import (
    ActivityEvent,
    AgingBucket,
    DashboardMetrics,
    DraftRequest,
    DraftResult,
    Invoice,
)
from .paypal_client import OPEN_STATUSES, PayPalError, create_paypal_client
from .sms_client import create_sms_client


app = FastAPI(title="Chaser API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

paypal = create_paypal_client()
ai = AIClient()
activity = ActivityLog(settings.activity_log)
sms = create_sms_client()


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
    if paypal.mode == "mock":
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
        "paypal_mode": paypal.mode,
        "ai_mode": "mock" if ai.mock_mode else "nebius",
        "sms_mode": sms.mode,
        "sending_enabled": False,
    }


@app.get("/api/dashboard", response_model=DashboardMetrics)
async def dashboard_metrics() -> DashboardMetrics:
    try:
        invoices = await _invoices()
        recovered = await paypal.recovered_revenue(date.today().replace(day=1))
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    bucket_specs = [
        ("current", "1–14 days", lambda days: days < 15),
        ("watch", "15–44 days", lambda days: 15 <= days < 45),
        ("critical", "45+ days", lambda days: days >= 45),
    ]
    buckets = [
        AgingBucket(
            key=key,
            label=label,
            invoice_count=sum(1 for invoice in invoices if predicate(invoice.days_overdue)),
            amount=sum(invoice.amount for invoice in invoices if predicate(invoice.days_overdue)),
        )
        for key, label, predicate in bucket_specs
    ]
    total = sum(invoice.amount for invoice in invoices)
    average = round(sum(invoice.days_overdue for invoice in invoices) / len(invoices)) if invoices else 0
    return DashboardMetrics(
        total_outstanding=total,
        average_days_overdue=average,
        critical_accounts=sum(1 for invoice in invoices if invoice.days_overdue >= 45),
        recovered_revenue=recovered,
        aging_buckets=buckets,
    )


@app.get("/api/invoices", response_model=list[Invoice])
async def list_invoices() -> list[Invoice]:
    try:
        return await _invoices()
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/mock/pay/{invoice_id}", response_class=HTMLResponse)
async def mock_payment_page(invoice_id: str) -> HTMLResponse:
    """Network-free stand-in for PayPal's hosted payer view."""
    if paypal.mode != "mock":
        raise HTTPException(status_code=404, detail="Mock payer view is disabled")
    try:
        invoice = Invoice.model_validate(await paypal.get_invoice(invoice_id))
    except PayPalError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Mock PayPal payment · {invoice.number}</title>
<style>body{{margin:0;background:#f5f7fa;color:#142c4f;font:16px Arial,sans-serif}}main{{max-width:520px;margin:10vh auto;padding:36px;border-radius:16px;background:white;box-shadow:0 18px 60px #183b6b20}}.logo{{font-size:22px;font-weight:800;color:#0878ce}}.mock{{display:inline-block;margin:14px 0;padding:5px 9px;border-radius:99px;background:#fff0c9;color:#715100;font-size:12px;font-weight:700}}h1{{margin:8px 0}}.amount{{font-size:36px;font-weight:800}}button{{width:100%;margin-top:24px;padding:14px;border:0;border-radius:24px;background:#0070ba;color:white;font-weight:700}}small{{display:block;margin-top:14px;color:#66788f;line-height:1.5}}</style></head>
<body><main><div class="logo">PayPal</div><span class="mock">CHASER MOCK · NO NETWORK PAYMENT</span><h1>{invoice.number}</h1><p>{invoice.customer_name}</p><p class="amount">{invoice.currency} {invoice.amount:,.2f}</p><button type="button" disabled>Payment simulated for demo</button><small>This local payer view proves the one-click handoff without contacting PayPal or collecting financial information.</small></main></body></html>"""
    return HTMLResponse(html)


@app.post("/api/invoices/{invoice_id}/draft", response_model=DraftResult)
async def create_draft(invoice_id: str, request: DraftRequest) -> DraftResult:
    try:
        invoice = next((item for item in await _invoices() if item.id == invoice_id), None)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    stage, rationale = choose_stage(invoice)
    channels, channel_rationale = choose_channels(invoice, stage)
    text_body = render_text(invoice, stage)
    try:
        subject, body, generated_by = await ai.draft(invoice, stage, rationale, request.context)
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    result = DraftResult(
        invoice_id=invoice.id,
        stage=stage,
        subject=subject,
        body=body,
        text_body=text_body,
        channels=channels,
        rationale=rationale,
        channel_rationale=channel_rationale,
        generated_by=generated_by,
    )
    if "text" in channels and invoice.customer_phone:
        await sms.send_text(invoice.customer_phone, text_body)
    activity.append(
        ActivityEvent(
            timestamp=datetime.now(UTC),
            invoice_id=invoice.id,
            invoice_number=invoice.number,
            stage=stage,
            channels=channels,
            tone_rationale=rationale,
            channel_rationale=channel_rationale,
            generated_by=generated_by,
        )
    )
    return result


@app.get("/api/activity")
async def list_activity(limit: int = 50) -> list[dict]:
    return activity.read(max(1, min(limit, 200)))
