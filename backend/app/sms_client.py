from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


logger = logging.getLogger("chaser.sms")


@dataclass(frozen=True)
class SMSMessage:
    to: str
    body: str


@runtime_checkable
class SMSClient(Protocol):
    """Provider seam used by Chaser; implementations may dispatch or record texts."""

    mode: str

    async def send_text(self, to: str, body: str) -> None: ...


class MockSMSClient:
    """Network-free adapter that records and logs messages instead of sending them."""

    mode = "mock"

    def __init__(self) -> None:
        self.messages: list[SMSMessage] = []

    async def send_text(self, to: str, body: str) -> None:
        message = SMSMessage(to=to, body=body)
        self.messages.append(message)
        logger.info("MOCK SMS to=%s body=%s", to, body)


def create_sms_client() -> SMSClient:
    # SMS is intentionally mock-only for the hackathon. A real adapter can satisfy
    # SMSClient later without changing routes, policy, or dashboard code.
    return MockSMSClient()
