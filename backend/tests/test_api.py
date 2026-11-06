from pathlib import Path

from fastapi.testclient import TestClient

from app.activity_log import ActivityLog
from app.sms_client import MockSMSClient
from app import main


def test_mock_flow_logs_draft(tmp_path: Path):
    main.activity = ActivityLog(tmp_path / "activity.jsonl")
    main.sms = MockSMSClient()
    client = TestClient(main.app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["paypal_mode"] == "mock"
    assert health.json()["sms_mode"] == "mock"
    assert health.json()["sending_enabled"] is False
    invoices = client.get("/api/invoices").json()
    assert len(invoices) >= 3
    assert all(invoice["payment_link"] for invoice in invoices)
    payer_view = client.get(invoices[0]["payment_link"].replace("http://localhost:8000", ""))
    assert payer_view.status_code == 200
    assert "NO NETWORK PAYMENT" in payer_view.text
    metrics = client.get("/api/dashboard")
    assert metrics.status_code == 200
    assert metrics.json()["recovered_revenue"] == 18_450
    assert {bucket["key"] for bucket in metrics.json()["aging_buckets"]} == {
        "current", "watch", "critical"
    }
    draft = client.post(f"/api/invoices/{invoices[0]['id']}/draft", json={})
    assert draft.status_code == 200
    assert draft.json()["stage"] == "nudge"
    assert draft.json()["channels"] == ["text"]
    assert len(main.sms.messages) == 1
    events = client.get("/api/activity").json()
    assert events[0]["invoice_id"] == invoices[0]["id"]
    assert events[0]["tone_rationale"]
    assert events[0]["channels"] == ["text"]
    assert events[0]["channel_rationale"]


def test_mock_flow_covers_all_escalation_stages_and_payment_links(tmp_path: Path):
    main.activity = ActivityLog(tmp_path / "all-stages.jsonl")
    main.sms = MockSMSClient()
    client = TestClient(main.app)
    invoices = client.get("/api/invoices").json()
    selected = {
        "nudge": next(item for item in invoices if item["number"] == "INV-1001"),
        "reminder": next(item for item in invoices if item["number"] == "INV-1002"),
        "final": next(item for item in invoices if item["number"] == "INV-1004"),
    }

    for expected_stage, invoice in selected.items():
        draft = client.post(f"/api/invoices/{invoice['id']}/draft", json={})
        assert draft.status_code == 200
        assert draft.json()["stage"] == expected_stage
        assert invoice["payment_link"] in draft.json()["body"]
        assert invoice["payment_link"] in draft.json()["text_body"]
        assert f"{invoice['currency']} {invoice['amount']:,.2f}" in draft.json()["text_body"]
        assert len(draft.json()["text_body"]) < 160
        assert draft.json()["channels"]
        assert draft.json()["channel_rationale"]
        assert draft.json()["rationale"]

    events = client.get("/api/activity").json()
    assert {event["stage"] for event in events} == {"nudge", "reminder", "final"}
    assert all(event["tone_rationale"] for event in events)
    assert all(event["channels"] for event in events)
    assert all(event["channel_rationale"] for event in events)
    assert len(main.sms.messages) == 3


def test_mock_api_flow_makes_no_outbound_http_calls(tmp_path: Path, monkeypatch):
    class NetworkForbidden:
        def __init__(self, *args, **kwargs):
            raise AssertionError("outbound network call attempted")

    monkeypatch.setattr("app.paypal_client.httpx.AsyncClient", NetworkForbidden)
    monkeypatch.setattr("app.ai_client.httpx.AsyncClient", NetworkForbidden)
    main.activity = ActivityLog(tmp_path / "offline.jsonl")
    main.sms = MockSMSClient()
    client = TestClient(main.app)

    assert client.get("/api/invoices").status_code == 200
    response = client.post("/api/invoices/INV2-DEMO-1002/draft", json={})
    assert response.status_code == 200
    assert response.json()["channels"] == ["email", "text"]
