from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Stage = Literal["nudge", "reminder", "final"]
Channel = Literal["email", "text"]


class Invoice(BaseModel):
    id: str
    number: str
    business_name: str
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    work_reference: str
    amount: float = Field(ge=0)
    currency: str = "USD"
    status: str
    due_date: str
    days_overdue: int = Field(ge=0)
    payment_link: str
    history_note: str = ""


class DraftRequest(BaseModel):
    context: str | None = Field(default=None, max_length=1000)


class DraftResult(BaseModel):
    invoice_id: str
    stage: Stage
    subject: str
    body: str
    text_body: str
    channels: list[Channel]
    rationale: str
    channel_rationale: str
    generated_by: Literal["mock", "nebius"]


class ActivityEvent(BaseModel):
    timestamp: datetime
    event: Literal["draft_created"] = "draft_created"
    invoice_id: str
    invoice_number: str
    stage: Stage
    channels: list[Channel]
    tone_rationale: str
    channel_rationale: str
    generated_by: Literal["mock", "nebius"]


class AgingBucket(BaseModel):
    key: Literal["current", "watch", "critical"]
    label: str
    invoice_count: int = Field(ge=0)
    amount: float = Field(ge=0)


class DashboardMetrics(BaseModel):
    total_outstanding: float = Field(ge=0)
    average_days_overdue: int = Field(ge=0)
    critical_accounts: int = Field(ge=0)
    recovered_revenue: float = Field(ge=0)
    aging_buckets: list[AgingBucket]
