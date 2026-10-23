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


def test_intent_provenance_deterministic(client):
    """Test that intent endpoints expose interpreter and parser_provenance safely."""
    resp = client.post("/api/intents/", json={
        "natural_language": "Guest users must not communicate with HR"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "interpreter" in data
    assert "parser_provenance" in data
    assert data["interpreter"] in ["deterministic", "deterministic_fallback"]
    assert data["parser_provenance"] == data["interpreter"]
    # Ensure no secrets or API keys are leaked
    assert "sk-" not in str(data)


def test_intent_provenance_mocked_llm(client):
    """Test that mocked OpenAI parsing preserves and exposes OpenAI interpreter provenance."""
    from unittest.mock import MagicMock, patch
    from app.config import Settings

    with patch("app.services.llm_parser.settings", Settings(openai_api_key="sk-mocked-test-key", openai_model="gpt-4o-mini")):
        mock_openai_module = MagicMock()
        mock_client = MagicMock()
        mock_openai_module.OpenAI.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = """{
            "status": "parsed",
            "confidence": 0.98,
            "assumptions": "Verified via LLM",
            "policies": [{
                "policy_type": "allow",
                "action": "permit",
                "source_zone": "finance",
                "destination_zone": "payroll",
                "protocol": "tcp",
                "port": "443"
            }]
        }"""
        mock_completion = MagicMock(choices=[mock_choice])
        mock_client.chat.completions.create.return_value = mock_completion

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            resp = client.post("/api/intents/", json={
                "natural_language": "Allow Finance to access Payroll on port 443"
            })
            assert resp.status_code == 201
            data = resp.json()
            assert data["interpreter"] == "openai-gpt-4o-mini"
            assert data["parser_provenance"] == "openai-gpt-4o-mini"
            assert "sk-" not in str(data)


def test_approve_repair_rejects_unvalidated_proposal(client, db_session):
    """Test that the API rejects approval of an unvalidated proposal with HTTP 400."""
    from app.services.verification_engine import VerificationEngine
    from app.services.repair_engine import RepairEngine
    from app.models.verification import VerificationFinding

    v_engine = VerificationEngine(db_session)
    run = v_engine.verify()
    finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(finding.id)
    assert proposal is not None
    assert proposal.validation_status == "pending"

    # Try approving without sandbox validation
    resp = client.post(f"/api/repairs/{proposal.id}/approve")
    assert resp.status_code == 400
    assert "sandbox validation" in resp.json()["detail"].lower()



