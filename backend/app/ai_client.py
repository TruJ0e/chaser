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
            "Draft a concise collections email. Return exactly two sections: "
            "SUBJECT: one line, then BODY: plain text. Do not threaten, invent fees, "
            "or claim legal action. "
            f"Stage: {stage}. Rationale: {rationale}. Invoice: {invoice.number}; "
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
        if stage == "nudge":
            return (
                f"Quick note about invoice {invoice.number}",
                f"Hi {invoice.customer_name},\n\nJust a friendly note that invoice {invoice.number} for {amount} is now {invoice.days_overdue} days past due. If it has already been handled, thank you and please disregard this message. Otherwise, you can review and pay it here: {invoice.payment_link}\n\nBest,\nChaser Accounts",
            )
        if stage == "reminder":
            return (
                f"Payment reminder: invoice {invoice.number}",
                f"Hi {invoice.customer_name},\n\nOur records show invoice {invoice.number} for {amount} remains unpaid {invoice.days_overdue} days after its due date. Please arrange payment or let us know if anything is holding it up. Payment details: {invoice.payment_link}\n\nThank you,\nChaser Accounts",
            )
        return (
            f"Final notice: invoice {invoice.number} is overdue",
            f"Hi {invoice.customer_name},\n\nThis is our final scheduled notice that invoice {invoice.number} for {amount} is {invoice.days_overdue} days overdue. Please make payment promptly or contact us today to discuss the account. Payment details: {invoice.payment_link}\n\nRegards,\nChaser Accounts",
        )
