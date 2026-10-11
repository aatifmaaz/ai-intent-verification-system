import pytest
from app.services.verification_engine import VerificationEngine
from app.services.repair_engine import RepairEngine
from app.models.verification import VerificationFinding

def test_propose_and_apply_repair(db_session):
    # Run initial verification to produce a failure
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()

    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()
    assert fail_finding is not None

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)

    assert proposal is not None
    assert proposal.change_type in ["acl_add", "acl_modify", "route_add"]
    assert proposal.approval_status == "pending"

    # Validate patch
    val = r_engine.validate_repair(proposal.id)
    assert val["valid"] is True

    # Apply repair
    success = r_engine.apply_repair(proposal.id)
    assert success is True
    assert proposal.approval_status == "approved"

    # Rollback repair
    rolled_back = r_engine.rollback_repair(proposal.id)
    assert rolled_back is True
    assert proposal.approval_status == "rolled_back"
