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

def test_invalid_repair_rejected(db_session):
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None

    # Corrupt proposal config to invalid structure
    proposal.proposed_config = {"acls": "not_a_list"}
    db_session.commit()

    val = r_engine.validate_repair(proposal.id)
    assert val["valid"] is False
    assert proposal.validation_status == "invalid"

    # Cannot apply invalid repair
    apply_res = r_engine.apply_repair(proposal.id)
    assert apply_res is False

def test_duplicate_apply_and_rollback_guard(db_session):
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None

    # Unapplied proposal cannot be rolled back
    assert r_engine.rollback_repair(proposal.id) is False

    # Validated and applied
    assert r_engine.validate_repair(proposal.id)["valid"] is True
    assert r_engine.apply_repair(proposal.id) is True

    # Duplicate apply rejected
    assert r_engine.apply_repair(proposal.id) is False

    # Rollback works
    assert r_engine.rollback_repair(proposal.id) is True

    # Double rollback rejected
    assert r_engine.rollback_repair(proposal.id) is False


def test_proposal_does_not_mutate_active_config(db_session):
    from app.models.device import Device
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    target_dev = db_session.query(Device).filter(Device.device_type.in_(["firewall", "router"])).first()
    original_config_before = dict(target_dev.config)

    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None

    # Verify device config in DB remains completely unchanged before approval
    db_session.refresh(target_dev)
    assert target_dev.config == original_config_before


def test_regression_detection_rejects_breaking_repair(db_session):
    from app.models.intent import Intent, NormalizedPolicy

    # Create a passing policy that traverses main-firewall: dmz to guest
    intent = Intent(natural_language="DMZ must access Guest network", status="parsed")
    db_session.add(intent)
    db_session.commit()
    pass_pol = NormalizedPolicy(
        intent_id=intent.id, policy_type="allow",
        source_zone="dmz", destination_zone="guest",
        protocol="ip", port="any", action="permit"
    )
    db_session.add(pass_pol)
    db_session.commit()

    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None

    # Case 1: Proposal that fails to satisfy target policy (explicitly allows violation)
    proposal.proposed_config = {
        "acls": [{
            "name": "still-broken",
            "rules": [
                {"action": "permit", "protocol": "ip", "source": "10.1.30.0/24", "destination": "10.1.10.0/24", "port": "any"}
            ]
        }]
    }
    db_session.commit()
    val_res1 = r_engine.validate_repair(proposal.id)
    assert val_res1["valid"] is False
    assert proposal.validation_status == "invalid"
    assert r_engine.apply_repair(proposal.id) is False

    # Case 2: Proposal that fixes target policy but introduces regression on passing policy (blocks dmz to guest)
    proposal.proposed_config = {
        "acls": [{
            "name": "fixes-target-breaks-others",
            "rules": [
                {"action": "deny", "protocol": "ip", "source": "10.1.30.0/24", "destination": "10.1.10.0/24", "port": "any"},
                {"action": "deny", "protocol": "ip", "source": "10.1.70.0/24", "destination": "10.1.30.0/24", "port": "any"}
            ]
        }]
    }
    db_session.commit()
    val_res2 = r_engine.validate_repair(proposal.id)
    assert val_res2["valid"] is False
    assert "break existing policy" in val_res2.get("error", "")
    assert proposal.validation_status == "invalid"
    assert r_engine.apply_repair(proposal.id) is False


def test_apply_before_validation_rejected(db_session):
    """Test that apply_repair rejects unvalidated proposals."""
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None
    assert proposal.validation_status == "pending"

    # Must be rejected because it hasn't passed sandbox validation
    assert r_engine.apply_repair(proposal.id) is False
    assert proposal.applied_at is None
    assert proposal.approval_status == "pending"


def test_stale_proposal_rejected(db_session):
    """Test that a proposal is marked stale and rejected if device config changes before apply."""
    from app.models.device import Device
    v_engine = VerificationEngine(db_session)
    run1 = v_engine.verify()
    fail_finding = db_session.query(VerificationFinding).filter(
        VerificationFinding.run_id == run1.id,
        VerificationFinding.status == "FAIL"
    ).first()

    r_engine = RepairEngine(db_session)
    proposal = r_engine.propose_repair(fail_finding.id)
    assert proposal is not None

    # First validate it so it becomes valid
    val = r_engine.validate_repair(proposal.id)
    assert val["valid"] is True
    assert proposal.validation_status == "valid"

    # Now simulate an external drift on the target device
    target_dev = db_session.query(Device).filter(Device.name == proposal.affected_devices[0]).first()
    target_dev.config = {"modified": "drifted_config"}
    db_session.commit()

    # Re-validating should detect staleness
    stale_val = r_engine.validate_repair(proposal.id)
    assert stale_val["valid"] is False
    assert proposal.validation_status == "stale"

    # Applying must be rejected
    assert r_engine.apply_repair(proposal.id) is False


