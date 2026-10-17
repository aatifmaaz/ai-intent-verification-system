import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

client = TestClient(app)

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "devices_count" in data
    assert "engine_version" in data

def test_list_scenarios():
    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 5
    assert scenarios[0]["id"] == "A"
    assert "Zero-Trust" in scenarios[0]["category"]

def test_run_scenario_a_and_reset():
    # Run Scenario A
    run_resp = client.post("/api/scenarios/A/run")
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["scenario_id"] == "A"
    assert len(data["findings"]) > 0

    # Reset baseline
    reset_resp = client.post("/api/scenarios/reset/baseline")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

def test_configurations_validate():
    valid_payload = {
        "format": "json",
        "content": '{"hostname": "router-test", "acls": []}'
    }
    resp = client.post("/api/configurations/validate", json=valid_payload)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

def test_audit_logs_search():
    resp = client.get("/api/audit-logs/?limit=10")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
