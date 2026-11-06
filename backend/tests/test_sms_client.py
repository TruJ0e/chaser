import logging
import asyncio

from app.sms_client import MockSMSClient


def test_mock_sms_records_and_logs_without_network(caplog):
    client = MockSMSClient()

    with caplog.at_level(logging.INFO, logger="chaser.sms"):
        asyncio.run(client.send_text("+15550100000", "USD 25.00 due. Pay: https://pay.test/i"))

    assert client.mode == "mock"
    assert len(client.messages) == 1
    assert client.messages[0].to == "+15550100000"
    assert client.messages[0].body == "USD 25.00 due. Pay: https://pay.test/i"
    assert "MOCK SMS" in caplog.text
