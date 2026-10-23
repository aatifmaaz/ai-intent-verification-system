import pytest
from app.services.scenario_runner import ScenarioRunner

def test_list_scenarios():
    runner = ScenarioRunner()
    scenarios = runner.get_scenarios()
    assert len(scenarios) == 5
    ids = [s["id"] for s in scenarios]
    assert "A" in ids
    assert "B" in ids
    assert "C" in ids
    assert "D" in ids
    assert "E" in ids

def test_run_scenario_a(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("A", db_session)
    assert res["scenario"] == "A"
    assert res["expected"] == "FAIL"
    assert len(res["findings"]) > 0
    assert res["findings"][0]["status"] == "FAIL"

def test_run_scenario_b_missing_route(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("B", db_session)
    assert res["scenario"] == "B"
    assert res["expected"] == "FAIL"
    assert len(res["findings"]) > 0
    assert res["findings"][0]["status"] == "FAIL"
    assert "Missing route" in res["findings"][0]["details"] or "blocked" in res["findings"][0]["details"]

def test_run_scenario_c_unauthorized_ssh(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("C", db_session)
    assert res["scenario"] == "C"
    assert res["expected"] == "FAIL"
    assert len(res["findings"]) > 0
    assert res["findings"][0]["status"] == "FAIL"

def test_run_scenario_d_db_exposure(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("D", db_session)
    assert res["scenario"] == "D"
    assert res["expected"] == "FAIL"
    assert len(res["findings"]) > 0
    assert res["findings"][0]["status"] == "FAIL"

def test_run_scenario_e_conflicts(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("E", db_session)
    assert res["scenario"] == "E"
    assert res["expected"] == "CONFLICT"
    assert len(res["conflicts"]) > 0
    assert "Contradictory" in res["conflicts"][0]

def test_scenario_a_repair_flow(db_session):
    from app.services.repair_engine import RepairEngine
    from app.services.verification_engine import VerificationEngine
    from app.models.verification import VerificationFinding

    runner = ScenarioRunner()
    res = runner.run_scenario("A", db_session)
    finding_id = res["findings"][0]["finding_id"]

    repair_engine = RepairEngine(db_session)
    proposal = repair_engine.propose_repair(finding_id)
    assert proposal is not None
    assert proposal.change_type == "acl_add"

    val_res = repair_engine.validate_repair(proposal.id)
    assert val_res["valid"] is True

    applied = repair_engine.apply_repair(proposal.id)
    assert applied is True

    # Re-verify post-repair
    v_engine = VerificationEngine(db_session)
    post_run = v_engine.verify()
    post_finding = db_session.query(VerificationFinding).filter_by(run_id=post_run.id).first()
    assert post_finding.status == "PASS"

