import json
import copy
import ipaddress
from datetime import datetime
from app.database import utc_now
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

        # Check if the failure was specifically caused by a missing route
        is_missing_route = False
        path_evals = (finding.evidence or {}).get('path_evaluations', [])
        for pe in path_evals:
            for hop in pe.get('hops', []):
                if "Missing route" in str(hop.get('reason', '')):
                    is_missing_route = True
                    break

        if is_missing_route:
            change_type = 'route_add'
            desc = f"Add missing static route to {policy.destination_zone or dst_net} on {target_device.name}"
            expected = f"Route to {dst_net} will be installed"
            
            dest_dev = self.db.query(Device).filter(Device.zone == policy.destination_zone).first()
            raw_dest = (dest_dev.subnet if dest_dev else None) or (dest_dev.ip_address if dest_dev else None) or dst_net
            if raw_dest and '/' in raw_dest:
                try:
                    net_obj = ipaddress.ip_network(raw_dest, strict=False)
                    route_net = str(net_obj.network_address)
                    route_mask = str(net_obj.netmask)
                except ValueError:
                    route_net = raw_dest.split('/')[0]
                    route_mask = "255.255.255.0"
            else:
                route_net = raw_dest if raw_dest and raw_dest != "any" else "10.1.6.0"
                route_mask = "255.255.255.0"

            proposed_config.setdefault('routes', []).append({
                "network": route_net,
                "mask": route_mask,
                "next_hop": "10.0.3.2"
            })
        elif ptype in ['deny', 'isolate']:
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

        try:
            from app.services.audit_service import AuditService
            AuditService.log(self.db, action="PROPOSE_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details=proposal.description)
        except Exception:
            pass

        return proposal

    def validate_repair(self, repair_id):
        proposal = self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        if not proposal:
            return {"valid": False, "error": "Proposal not found"}
            
        # Validate configuration structure
        proposed = proposal.proposed_config or {}
        if not isinstance(proposed, dict):
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "Invalid configuration structure: must be an object"}

        if 'acls' in proposed:
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

        if 'routes' in proposed:
            if not isinstance(proposed['routes'], list):
                proposal.validation_status = "invalid"
                self.db.commit()
                return {"valid": False, "error": "Routes collection must be a list"}
            for r in proposed['routes']:
                if not isinstance(r, dict) or 'network' not in r:
                    proposal.validation_status = "invalid"
                    self.db.commit()
                    return {"valid": False, "error": "Each route must be an object with network"}

        target_policy = self.db.query(NormalizedPolicy).filter_by(id=proposal.policy_id).first()
        target_device_name = (proposal.affected_devices or [None])[0]
        target_device = self.db.query(Device).filter_by(name=target_device_name).first()
        if not target_policy or not target_device:
            proposal.validation_status = "invalid"
            self.db.commit()
            return {"valid": False, "error": "Repair target or policy no longer exists"}

        # Stale check: verify target device config hasn't drifted since proposal generation
        if proposal.original_config and target_device.config != proposal.original_config:
            proposal.validation_status = "stale"
            self.db.commit()
            return {"valid": False, "error": f"Device {target_device.name} configuration has changed since proposal was generated (proposal is stale)"}

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
            
        # Safety check: Cannot apply an already applied repair
        if proposal.applied_at or proposal.approval_status == "approved":
            return False

        # Safety check: Must have passed sandbox validation first
        if proposal.validation_status != "valid":
            return False

        # Safety check: Reject stale proposal if device config changed since generation
        for dev_name in (proposal.affected_devices or []):
            dev = self.db.query(Device).filter(Device.name == dev_name).first()
            if dev and proposal.original_config:
                if dev.config != proposal.original_config:
                    proposal.validation_status = "stale"
                    self.db.commit()
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
                    created_at=utc_now()
                )
                self.db.add(version)
                dev.config = proposal.proposed_config
                
        proposal.approval_status = "approved"
        proposal.approved_at = utc_now()
        proposal.applied_at = utc_now()
        self.db.commit()

        try:
            from app.services.audit_service import AuditService
            AuditService.log(self.db, action="APPLY_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details={"change_type": proposal.change_type, "devices": proposal.affected_devices})
        except Exception:
            pass

        return True

    def rollback_repair(self, repair_id):
        proposal = self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        if not proposal or not proposal.applied_at or proposal.rolled_back_at:
            return False
            
        for dev_name in (proposal.affected_devices or []):
            dev = self.db.query(Device).filter(Device.name == dev_name).first()
            if dev:
                version_count = self.db.query(ConfigurationVersion).filter(ConfigurationVersion.device_id == dev.id).count()
                version = ConfigurationVersion(
                    device_id=dev.id,
                    version_number=version_count + 1,
                    config_data=dev.config,
                    change_description=f"Rollback of proposal {proposal.id}: {proposal.description}",
                    created_at=utc_now()
                )
                self.db.add(version)
                dev.config = proposal.original_config
                
        proposal.approval_status = "rolled_back"
        proposal.rolled_back_at = utc_now()
        self.db.commit()

        try:
            from app.services.audit_service import AuditService
            AuditService.log(self.db, action="ROLLBACK_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details={"devices": proposal.affected_devices})
        except Exception:
            pass

        return True

