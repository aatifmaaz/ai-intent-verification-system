import pytest
from app.services.verification_engine import VerificationEngine
from app.models.verification import VerificationFinding

def test_verification_engine_run(db_session):
    engine = VerificationEngine(db_session)
    run = engine.verify()

    assert run.total_policies >= 5
    assert run.passed >= 1
    assert run.failed >= 1
    assert run.status == "completed"

    findings = db_session.query(VerificationFinding).filter(VerificationFinding.run_id == run.id).all()
    assert len(findings) == run.total_policies

    # Check that each finding has evidence and severity assigned
    for f in findings:
        assert f.status in ["PASS", "FAIL", "UNKNOWN"]
        assert f.severity in ["critical", "high", "medium", "low", "info"]
        assert f.evidence is not None

def test_guest_isolation_violation_detected(db_session):
    engine = VerificationEngine(db_session)
    run = engine.verify()

    # Finding 1 corresponds to policy 1: Guest must not communicate with HR
    finding_1 = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run.id,
        VerificationFinding.policy_id == 1
    ).first()

    assert finding_1 is not None
    assert finding_1.status == "FAIL"
    assert "guest" in finding_1.details.lower()
