from datetime import datetime
import json
from app.models import Device, NetworkLink, NormalizedPolicy, VerificationRun, VerificationFinding
from app.services.network_graph import NetworkGraph

class VerificationEngine:
    def __init__(self, db_session):
        self.db = db_session

    def verify(self):
        devices = self.db.query(Device).all()
        links = self.db.query(NetworkLink).all()
        policies = self.db.query(NormalizedPolicy).all()

        run = VerificationRun(
            started_at=datetime.utcnow(),
            total_policies=len(policies),
            status="running"
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        graph = NetworkGraph(devices, links)
        passed = 0
        failed = 0
        unknown = 0

        for policy in policies:
            finding = self._evaluate_policy(graph, policy, run.id)
            if finding.status == "PASS":
                passed += 1
            elif finding.status == "FAIL":
                failed += 1
            else:
                unknown += 1
            self.db.add(finding)

        run.completed_at = datetime.utcnow()
        run.passed = passed
        run.failed = failed
        run.unknown = unknown
        run.status = "completed"
        self.db.commit()
        
        return run

    def _evaluate_policy(self, graph, policy, run_id):
        src_zone = policy.source_zone
        dst_zone = policy.destination_zone
        protocol = policy.protocol
        port = policy.port
        ptype = policy.policy_type.lower()
        
        src_devices = graph.get_devices_in_zone(src_zone)
        dst_devices = graph.get_devices_in_zone(dst_zone)
        
        if not src_devices or not dst_devices:
            return VerificationFinding(
                run_id=run_id, policy_id=policy.id, status="UNKNOWN",
                severity="low", risk_level="low", affected_devices=[],
                affected_networks=[], evidence={"reason": "Missing devices in zones"},
                remediation="Add devices to zones", details="Zones lack devices."
            )

        missing_config = False
        for dev in src_devices + dst_devices:
            d_data = graph.graph.nodes[dev]
            if not d_data.get('config'):
                missing_config = True
                
        if missing_config:
            return VerificationFinding(
                run_id=run_id, policy_id=policy.id, status="UNKNOWN",
                severity="medium", risk_level="medium", affected_devices=[],
                affected_networks=[], evidence={"reason": "Missing config data on endpoints"},
                remediation="Ensure configuration is pulled for all devices",
                details="Cannot verify due to missing configuration data."
            )

        evidence_list = graph.get_path_evidence(src_zone, dst_zone, protocol, port)
        has_permitted = any(e['permitted'] for e in evidence_list)
        
        status = "UNKNOWN"
        remediation = ""
        details = ""
        affected = set()
        
        for e in evidence_list:
            for p in e['path']:
                affected.add(p)
                
        if ptype in ['deny', 'isolate']:
            if has_permitted:
                status = "FAIL"
                details = f"Traffic permitted from {src_zone} to {dst_zone} but should be denied."
                remediation = "Add deny rules to intermediate firewalls."
            else:
                status = "PASS"
                details = f"Traffic correctly isolated from {src_zone} to {dst_zone}."
        elif ptype in ['allow', 'require']:
            if has_permitted:
                status = "PASS"
                details = f"Traffic correctly allowed from {src_zone} to {dst_zone}."
            else:
                status = "FAIL"
                details = f"Traffic blocked from {src_zone} to {dst_zone} but should be allowed."
                remediation = "Add permit rules or routes to intermediate devices."
        elif ptype == 'restrict':
            # Simplified restrict check: check if it's permitted, but in reality we should check other sources
            if has_permitted:
                status = "PASS"
                details = f"Traffic permitted for restricted policy."
            else:
                status = "FAIL"
                details = f"Restricted traffic is blocked."
                remediation = "Ensure authorized sources can reach destination."
        
        severity = "high"
        if status == "FAIL" and ptype in ['deny', 'isolate']:
            severity = "critical"
            
        risk_level = severity
            
        return VerificationFinding(
            run_id=run_id,
            policy_id=policy.id,
            status=status,
            severity=severity,
            risk_level=risk_level,
            affected_devices=list(affected),
            affected_networks=[policy.source_network, policy.destination_network] if policy.source_network else [],
            evidence={"path_evaluations": evidence_list},
            remediation=remediation,
            details=details
        )
