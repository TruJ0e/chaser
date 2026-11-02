from __future__ import annotations

from .models import Invoice, Stage


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
