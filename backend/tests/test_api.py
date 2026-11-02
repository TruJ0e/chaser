from pathlib import Path

from fastapi.testclient import TestClient

from app.activity_log import ActivityLog
from app import main


def test_mock_flow_logs_draft(tmp_path: Path):
    main.activity = ActivityLog(tmp_path / "activity.jsonl")
    client = TestClient(main.app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["sending_enabled"] is False
    invoices = client.get("/api/invoices").json()
    assert len(invoices) >= 3
    draft = client.post(f"/api/invoices/{invoices[0]['id']}/draft", json={})
    assert draft.status_code == 200
    assert draft.json()["stage"] == "nudge"
    events = client.get("/api/activity").json()
    assert events[0]["invoice_id"] == invoices[0]["id"]
    assert events[0]["tone_rationale"]
