import json
import copy
from datetime import datetime
from app.models import RepairProposal, VerificationFinding, Intent, NormalizedPolicy, Device, NetworkLink, ConfigurationVersion
from app.services.network_graph import NetworkGraph
from app.services.verification_engine import VerificationEngine

class RepairEngine:
    def __init__(self, db_session):
        self.db = db_session

    def propose_repair(self, finding_id):
        finding = self.db.query(VerificationFinding).filter_by(id=finding_id).first()
        if not finding or finding.status != "FAIL":
            return None
            
        policy = self.db.query(NormalizedPolicy).filter_by(id=finding.policy_id).first()
        
        # Determine violation type
        ptype = policy.policy_type.lower()
        
        # A repair point must lie on every evaluated route. Choosing any
        # firewall/router from the union of affected devices can miss an
        # alternate path, such as the distribution-switch trunk.
        target_device = None
        path_sets = [
            set(item.get('path', []))
            for item in (finding.evidence or {}).get('path_evaluations', [])
            if item.get('path')
        ]
        common_path_names = set.intersection(*path_sets) if path_sets else set()
        candidates = self.db.query(Device).filter(Device.name.in_(common_path_names)).all() if common_path_names else []
        for device_type in ('firewall', 'router', 'switch'):
            typed = [device for device in candidates if device.device_type == device_type]
            if typed:
                target_device = typed[0]
                break

        if not target_device:
            return None
            
        current_config = target_device.config if isinstance(target_device.config, dict) else json.loads(target_device.config or '{}')
        proposed_config = json.loads(json.dumps(current_config)) # Deep copy
        
        change_type = ""
        desc = ""
        expected = ""
        
        acls = proposed_config.get('acls', [])
        if not acls:
            acls = [{"name": "auto-remediation-acl", "rules": []}]
            proposed_config['acls'] = acls
            
        target_acl = acls[0]
        
        # Resolve source/dest subnets from policy or zone
        src_net = policy.source_network
        if (not src_net or src_net == "any") and policy.source_zone:
            src_dev = self.db.query(Device).filter(Device.zone == policy.source_zone).first()
            if src_dev and src_dev.subnet:
                src_net = src_dev.subnet

        dst_net = policy.destination_network
        if (not dst_net or dst_net == "any") and policy.destination_zone:
            dst_dev = self.db.query(Device).filter(Device.zone == policy.destination_zone).first()
            if dst_dev and dst_dev.subnet:
                dst_net = dst_dev.subnet

        src_net = src_net or "any"
        dst_net = dst_net or "any"

        if ptype in ['deny', 'isolate']:
            change_type = 'acl_add'
            desc = f"Add deny rule to block {policy.source_zone or src_net} to {policy.destination_zone or dst_net}"
            expected = f"Traffic from {src_net} to {dst_net} will be blocked"
            target_acl['rules'].insert(0, {
                "action": "deny",
                "protocol": policy.protocol or "ip",
                "source": src_net,
                "destination": dst_net,
                "port": policy.port or "any"
            })
            
        elif ptype in ['allow', 'require']:
            change_type = 'acl_add'
            desc = f"Add permit rule to allow {policy.source_zone or src_net} to {policy.destination_zone or dst_net}"
            expected = f"Traffic from {src_net} to {dst_net} will be permitted"
            target_acl['rules'].insert(0, {
                "action": "permit",
                "protocol": policy.protocol or "ip",
                "source": src_net,
                "destination": dst_net,
                "port": policy.port or "any"
            })
        else:
            change_type = 'acl_modify'
            desc = f"Restrict access to {policy.destination_zone or dst_net}"
            expected = "Access restricted to authorized management sources"
            target_acl['rules'].insert(0, {
                "action": "permit",
                "protocol": policy.protocol or "tcp",
                "source": src_net if src_net != "any" else "10.1.40.0/24",
                "destination": dst_net,
                "port": policy.port or 22
            })
            
        proposal = RepairProposal(
            finding_id=finding.id,
            policy_id=policy.id,
            description=desc,
            original_config=current_config,
            proposed_config=proposed_config,
            change_type=change_type,
            affected_devices=[target_device.name],
            expected_result=expected,
            validation_status="pending",
            approval_status="pending"
        )
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def validate_repair(self, repair_id):
        proposal = self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        if not proposal:
            return {"valid": False, "error": "Proposal not found"}
            
        # Validate ACL shape and rule values before evaluating the proposed
        # configuration against an isolated copy of the live graph.
        proposed = proposal.proposed_config or {}
        if not isinstance(proposed, dict) or 'acls' not in proposed:
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "Invalid configuration structure"}

        if not isinstance(proposed['acls'], list):
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "ACL collection must be a list"}

        for acl in proposed['acls']:
            if not isinstance(acl, dict) or not isinstance(acl.get('rules'), list):
                proposal.validation_status = "invalid"
                self.db.commit()
                return {"valid": False, "error": "Each ACL must contain a rule list"}
            for rule in acl['rules']:
                if not isinstance(rule, dict) or rule.get('action') not in {'permit', 'deny'}:
                    proposal.validation_status = "invalid"
                    self.db.commit()
                    return {"valid": False, "error": "ACL rules must have a permit or deny action"}

        target_policy = self.db.query(NormalizedPolicy).filter_by(id=proposal.policy_id).first()
        target_device_name = (proposal.affected_devices or [None])[0]
        target_device = self.db.query(Device).filter_by(name=target_device_name).first()
        if not target_policy or not target_device:
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "Repair target or policy no longer exists"}

        devices = self.db.query(Device).all()
        links = self.db.query(NetworkLink).all()
        before_graph = NetworkGraph(devices, links)
        simulated_devices = []
        for device in devices:
            if device.id == target_device.id:
                simulated_device = copy.copy(device)
                simulated_device.config = proposed
                simulated_devices.append(simulated_device)
            else:
                simulated_devices.append(device)
        after_graph = NetworkGraph(simulated_devices, links)
        verifier = VerificationEngine(self.db)
        after_target = verifier._evaluate_policy(after_graph, target_policy, None)
        if after_target.status != "PASS":
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "Proposed ACL does not satisfy the requested policy on the full topology"}

        policies = (
            self.db.query(NormalizedPolicy)
            .join(Intent, Intent.id == NormalizedPolicy.intent_id)
            .filter((Intent.status.is_(None)) | (Intent.status != "archived"))
            .all()
        )
        for existing_policy in policies:
            if existing_policy.id == target_policy.id:
                continue
            before = verifier._evaluate_policy(before_graph, existing_policy, None)
            if before.status != "PASS":
                continue
            after = verifier._evaluate_policy(after_graph, existing_policy, None)
            if after.status == "FAIL":
                proposal.validation_status = "invalid"
                self.db.commit()
                return {"valid": False, "error": f"Proposed ACL would break existing policy {existing_policy.id}"}

        proposal.validation_status = "valid"
        self.db.commit()
        return {"valid": True, "status": "valid", "message": "ACL schema, requested policy, and passing-policy regressions validated in an isolated graph"}

    def apply_repair(self, repair_id):
        proposal = self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        if not proposal:
            return False
            
        for dev_name in (proposal.affected_devices or []):
            dev = self.db.query(Device).filter(Device.name == dev_name).first()
            if dev:
                # Save old configuration version
                version_count = self.db.query(ConfigurationVersion).filter(ConfigurationVersion.device_id == dev.id).count()
                version = ConfigurationVersion(
                    device_id=dev.id,
                    version_number=version_count + 1,
                    config_data=dev.config,
                    change_description=proposal.description,
                    created_at=datetime.utcnow()
                )
                self.db.add(version)
                dev.config = proposal.proposed_config
                
        proposal.approval_status = "approved"
        proposal.approved_at = datetime.utcnow()
        proposal.applied_at = datetime.utcnow()
        self.db.commit()
        return True

    def rollback_repair(self, repair_id):
        proposal = self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        if not proposal or not proposal.applied_at:
            return False
            
        for dev_name in (proposal.affected_devices or []):
            dev = self.db.query(Device).filter(Device.name == dev_name).first()
            if dev:
                dev.config = proposal.original_config
                
        proposal.approval_status = "rolled_back"
        proposal.rolled_back_at = datetime.utcnow()
        self.db.commit()
        return True

