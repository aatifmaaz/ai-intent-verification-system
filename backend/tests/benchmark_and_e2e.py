"""
Reproducible Benchmark and End-to-End Workflow Verification Script.
Measures verification and repair validation performance using time.monotonic().
"""

import time
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Device, NetworkLink, Intent, NormalizedPolicy, VerificationFinding, ConfigurationVersion, AuditEvent
from app.services.intent_parser import IntentParser
from app.services.network_graph import NetworkGraph
from app.services.verification_engine import VerificationEngine
from app.services.repair_engine import RepairEngine
from app.services.scenario_runner import ScenarioRunner


def run_benchmark():
    print("=" * 60)
    print("STARTING DETERMINISTIC PERFORMANCE BENCHMARK")
    print("=" * 60)

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    scales = [
        {"nodes": 10, "links": 15, "policies": 5},
        {"nodes": 25, "links": 40, "policies": 15},
        {"nodes": 50, "links": 90, "policies": 30},
    ]

    for scale in scales:
        n_nodes = scale["nodes"]
        n_links = scale["links"]
        n_pols = scale["policies"]

        # Clear tables
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

        # Seed devices partitioned across distinct security zones
        num_zones = max(2, n_nodes // 5)
        for i in range(n_nodes):
            zone_idx = i % num_zones
            dev = Device(
                id=i + 1,
                name=f"dev-{i+1}",
                device_type="router" if i % 5 == 0 else "server",
                ip_address=f"10.{zone_idx}.0.{i + 1}",
                subnet="255.255.255.0",
                zone=f"zone_{zone_idx}",
                status="active",
                config={"interfaces": ["eth0"], "acls": []}
            )
            db.add(dev)
        db.commit()

        # Seed links (backbone linear plus interconnects)
        link_id = 1
        for i in range(1, n_nodes):
            link = NetworkLink(
                id=link_id,
                source_device_id=i,
                target_device_id=i + 1,
                status="active"
            )
            db.add(link)
            link_id += 1
        extra = n_links - (n_nodes - 1)
        for e in range(extra):
            src = (e % (n_nodes - 2)) + 1
            tgt = ((src + 2) % n_nodes) + 1
            link = NetworkLink(
                id=link_id,
                source_device_id=src,
                target_device_id=tgt,
                status="active"
            )
            db.add(link)
            link_id += 1
        db.commit()

        # Seed Intent
        intent = Intent(
            id=1,
            natural_language="Benchmark policy set",
            status="active"
        )
        db.add(intent)
        db.commit()

        # Seed policies between distinct zone pairs
        for p in range(n_pols):
            action = "deny" if p % 2 == 0 else "allow"
            src_z = f"zone_{p % num_zones}"
            dst_z = f"zone_{(p + 1) % num_zones}"
            pol = NormalizedPolicy(
                id=p + 1,
                intent_id=1,
                policy_type=action,
                action="permit" if action == "allow" else "deny",
                source_zone=src_z,
                destination_zone=dst_z,
                protocol="ip",
                port="any",
                priority=100
            )
            db.add(pol)
        db.commit()

        # Benchmark verification engine with monotonic clock
        v_engine = VerificationEngine(db)
        
        REPETITIONS = 3
        times = []
        for _ in range(REPETITIONS):
            t0 = time.monotonic()
            run_result = v_engine.verify()
            t1 = time.monotonic()
            times.append(t1 - t0)

        avg_time_ms = (sum(times) / len(times)) * 1000
        min_time_ms = min(times) * 1000
        max_time_ms = max(times) * 1000

        print(f"Scale: {n_nodes:2d} nodes | {n_links:2d} links | {n_pols:2d} policies "
              f"-> Avg: {avg_time_ms:6.2f} ms | Min: {min_time_ms:6.2f} ms | Max: {max_time_ms:6.2f} ms "
              f"| Verified: Passed={run_result.passed}, Failed={run_result.failed}, Unknown={run_result.unknown}")

    db.close()


def run_e2e_lifecycle():
    print("\n" + "=" * 60)
    print("RUNNING END-TO-END LIFECYCLE DEMONSTRATION")
    print("=" * 60)

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Step 1: Load Scenario A (Guest isolation violation)
    runner = ScenarioRunner(db)
    scen_info = runner.run_scenario("A")
    print(f"1. Scenario A loaded. Initial findings: {len(scen_info['findings'])}")
    assert len(scen_info["findings"]) > 0
    fail_finding = [f for f in scen_info["findings"] if f["status"] == "FAIL"][0]
    print(f"   Detected expected violation: Finding ID {fail_finding['finding_id']} - {fail_finding['details']}")

    # Step 2: Propose repair & validate in sandbox
    repair_engine = RepairEngine(db)
    proposal = repair_engine.propose_repair(fail_finding["finding_id"])
    assert proposal is not None
    print(f"2. Repair proposal created: ID={proposal.id}, Type={proposal.change_type}")
    print(f"   Affected devices: {proposal.affected_devices}")

    val_res = repair_engine.validate_repair(proposal.id)
    assert val_res["valid"] is True
    assert proposal.validation_status == "valid"
    print(f"   Sandbox dry-run & regression validation: valid={val_res['valid']}, message={val_res['message']}")

    # Step 3: Apply repair
    applied = repair_engine.apply_repair(proposal.id)
    assert applied is True
    print(f"3. Repair applied successfully to simulated state.")

    # Step 4: Re-verify
    v_engine = VerificationEngine(db)
    post_run = v_engine.verify()
    post_findings = db.query(VerificationFinding).filter_by(run_id=post_run.id).all()
    violation_resolved = all(f.status != "FAIL" for f in post_findings)
    print(f"4. Re-verification run: All violations resolved = {violation_resolved} (Passed={post_run.passed}, Failed={post_run.failed})")
    assert violation_resolved is True

    # Step 5: Rollback repair
    rolled_back = repair_engine.rollback_repair(proposal.id)
    assert rolled_back is True
    print(f"5. Rollback executed successfully.")

    # Step 6: Verify restored state
    restored_run = v_engine.verify()
    restored_findings = db.query(VerificationFinding).filter_by(run_id=restored_run.id).all()
    restored_violation = any(f.status == "FAIL" for f in restored_findings)
    print(f"6. Verification post-rollback: Violation restored = {restored_violation} (Passed={restored_run.passed}, Failed={restored_run.failed})")
    assert restored_violation is True

    # Step 7: Audit log verification
    audits = db.query(AuditEvent).all()
    print(f"7. Audit trail records created: {len(audits)} events logged.")
    assert len(audits) >= 3

    print("\nALL END-TO-END CRITERIA VERIFIED SUCCESSFULLY!")
    db.close()


if __name__ == "__main__":
    run_benchmark()
    run_e2e_lifecycle()
