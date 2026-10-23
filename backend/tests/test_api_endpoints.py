import pytest
from app.models.intent import Intent, NormalizedPolicy

def test_system_status(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "devices_count" in data
    assert "engine_version" in data

def test_list_scenarios(client):
    response = client.get("/api/scenarios/")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 5
    assert scenarios[0]["id"] == "A"
    assert "Zero-Trust" in scenarios[0]["category"]

def test_run_scenario_a_and_reset(client):
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

def test_configurations_validate(client):
    valid_payload = {
        "format": "json",
        "content": '{"hostname": "router-test", "acls": []}'
    }
    resp = client.post("/api/configurations/validate", json=valid_payload)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

def test_audit_logs_search(client):
    resp = client.get("/api/audit-logs/?limit=10")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)

def test_auto_enforce_intent(client):
    resp = client.post("/api/intents/auto-enforce", json={
        "natural_language": "The guest network must not communicate with the HR network."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["REMEDIATED", "COMPLIANT"]
    assert len(data["steps"]) >= 3

def test_update_intent_reparses_policy(client, db_session):
    intent = Intent(natural_language="Guest users must not communicate with HR", status="parsed")
    db_session.add(intent)
    db_session.commit()
    response = client.put(f"/api/intents/{intent.id}", json={
        "natural_language": "Engineering should have access to the application server"
    })
    assert response.status_code == 200
    policy = db_session.query(NormalizedPolicy).filter_by(intent_id=intent.id).one()
    assert policy.policy_type == "allow"
    assert policy.action == "permit"
    assert policy.source_zone == "engineering"
    assert policy.destination_zone == "application"


