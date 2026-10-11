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

def test_run_scenario_e_conflicts(db_session):
    runner = ScenarioRunner()
    res = runner.run_scenario("E", db_session)
    assert res["scenario"] == "E"
    assert res["expected"] == "CONFLICT"
    assert len(res["conflicts"]) > 0
