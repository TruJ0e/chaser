from __future__ import annotations

import httpx

from .config import Settings, settings
from .models import Invoice, Stage


class AIClientError(RuntimeError):
    pass


class AIClient:
    """OpenAI-compatible chat-completions client with deterministic local fallback."""

    def __init__(self, config: Settings = settings, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = config.nebius_base_url.rstrip("/")
        self.api_key = config.nebius_api_key
        self.model = config.nebius_model
        self.mock_mode = not (self.base_url and self.api_key)
        self._transport = transport

    async def draft(
        self, invoice: Invoice, stage: Stage, rationale: str, context: str | None = None
    ) -> tuple[str, str, str]:
        if self.mock_mode:
            subject, body = self._mock_draft(invoice, stage)
            return subject, body, "mock"

        prompt = (
            f"Write as {invoice.business_name}, not as a collections service. Draft a concise "
            "payment follow-up that sounds like a real continuation of this customer relationship, "
            "never a generic template. Lead with who the business is and the specific work completed, "
            "then naturally include the invoice number, amount, days overdue, and payment link. "
            "Use the relationship history to make the note personal without exposing internal labels. "
            f"Sign as {invoice.business_name}. Never use 'Chaser Accounts', 'our records show', or "
            "'final scheduled notice'. Return exactly two sections: SUBJECT: one line, then BODY: "
            "plain text. Do not threaten, invent fees, or claim legal action. "
            f"Stage: {stage}. Rationale: {rationale}. Invoice: {invoice.number}; "
            f"business: {invoice.business_name}; work completed: {invoice.work_reference}; "
            f"customer: {invoice.customer_name}; amount: {invoice.currency} {invoice.amount:.2f}; "
            f"days overdue: {invoice.days_overdue}; payment link: {invoice.payment_link}. "
            f"Relationship history: {invoice.history_note}. Additional context: {context or 'none'}."
        )
        async with httpx.AsyncClient(transport=self._transport, timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": "You write respectful, accurate accounts-receivable emails."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
        try:
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise AIClientError("The OpenAI-compatible draft request failed") from exc
        subject, separator, body = text.partition("BODY:")
        if not separator:
            raise AIClientError("AI response did not contain the required BODY section")
        subject = subject.removeprefix("SUBJECT:").strip()
        return subject, body.strip(), "nebius"

    @staticmethod
    def _mock_draft(invoice: Invoice, stage: Stage) -> tuple[str, str]:
        amount = f"{invoice.currency} {invoice.amount:,.2f}"
        relationship_open = (
            f"Hi {invoice.customer_name},\n\n{invoice.business_name} here, following up on "
            f"{invoice.work_reference}. {invoice.history_note}"
        )
        if stage == "nudge":
            return (
                f"A quick note on {invoice.work_reference} · {invoice.number}",
                f"{relationship_open}\n\nInvoice {invoice.number} for {amount} is {invoice.days_overdue} days overdue. If you have already handled it, thank you; otherwise, you can review and pay it here: {invoice.payment_link}\n\nBest,\n{invoice.business_name}",
            )
        if stage == "reminder":
            return (
                f"Checking in on {invoice.work_reference} · {invoice.number}",
                f"{relationship_open}\n\nInvoice {invoice.number} for {amount} is now {invoice.days_overdue} days overdue. Please take care of it here, or reply if there is anything we should sort out together: {invoice.payment_link}\n\nThank you,\n{invoice.business_name}",
            )
        return (
            f"Please reply about {invoice.work_reference} · {invoice.number}",
            f"{relationship_open}\n\nInvoice {invoice.number} for {amount} is {invoice.days_overdue} days overdue, and we need to close the loop. Please pay it here or reply today so we can understand what is holding it up: {invoice.payment_link}\n\nRegards,\n{invoice.business_name}",
        )
