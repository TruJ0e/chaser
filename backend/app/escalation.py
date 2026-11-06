from __future__ import annotations

from .models import Channel, Invoice, Stage


def choose_stage(invoice: Invoice) -> tuple[Stage, str]:
    """Apply a transparent three-stage ladder using age and balance risk."""
    days = invoice.days_overdue
    amount = invoice.amount

    if days >= 45 or (days >= 30 and amount >= 10_000):
        stage: Stage = "final"
        reason = "final notice because the invoice is materially aged"
        if days < 45:
            reason += " and the balance is at least USD 10,000"
    elif days >= 15 or (days >= 7 and amount >= 5_000):
        stage = "reminder"
        reason = "firm, professional reminder because follow-up is now warranted"
        if days < 15:
            reason += " for a balance of at least USD 5,000"
    else:
        stage = "nudge"
        reason = "friendly nudge because the invoice is only recently overdue"

    rationale = (
        f"Selected a {reason}: {days} days overdue with an outstanding "
        f"{invoice.currency} {amount:,.2f}. {invoice.history_note}"
    )
    return stage, rationale


def choose_channels(invoice: Invoice, stage: Stage) -> tuple[list[Channel], str]:
    """Pick outreach channels with an auditable, deterministic policy."""
    if not invoice.customer_phone:
        return ["email"], "Selected email because no customer mobile number is available."
    if stage == "nudge" and "concise" in invoice.history_note.lower():
        return ["text"], "Selected text for a low-pressure nudge because this customer prefers concise messages."
    if stage in {"reminder", "final"}:
        return ["email", "text"], (
            f"Selected email and text because this {stage} stage warrants clear written detail "
            "and a short mobile reminder."
        )
    return ["email"], "Selected email for the first friendly follow-up to keep the outreach low pressure."


def render_text(invoice: Invoice, stage: Stage) -> str:
    """Render a single-segment SMS with amount and direct payment link."""
    amount = f"{invoice.currency} {invoice.amount:,.2f}"
    copy = {
        "nudge": f"Friendly reminder: {amount} is due. Pay here: {invoice.payment_link}",
        "reminder": f"Payment reminder: {amount} remains overdue. Pay here: {invoice.payment_link}",
        "final": f"Final notice: {amount} remains overdue. Please pay or contact us today: {invoice.payment_link}",
    }[stage]
    if len(copy) > 160:
        raise ValueError("SMS draft exceeds 160 characters; use a shorter payment link")
    return copy
