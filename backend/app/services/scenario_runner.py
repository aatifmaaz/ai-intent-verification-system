from app.models import Device, NetworkLink, Intent, NormalizedPolicy, VerificationFinding
from app.services.verification_engine import VerificationEngine
from app.services.repair_engine import RepairEngine
import json

class ScenarioRunner:
    def __init__(self, db=None):
        self.db = db

    def get_scenarios(self):
        return [
            {"id": "A", "name": "Guest Isolation Violation", "description": "Guest network can reach HR network."},
            {"id": "B", "name": "Missing Route", "description": "Engineering devices cannot reach app server."},
            {"id": "C", "name": "Unauthorized SSH", "description": "Core router allows SSH from anywhere."},
            {"id": "D", "name": "Database Exposure", "description": "Database accessible from guest."},
            {"id": "E", "name": "Conflicting Intents", "description": "Two conflicting policies on DB access."}
        ]

    def run_scenario(self, scenario_id, db=None):
        db = db or self.db
        if db is None:
            raise ValueError("Database session required")
        # Clean DB for demo scenario
        db.query(VerificationFinding).delete()
        db.query(NormalizedPolicy).delete()
        db.query(Intent).delete()
        db.query(NetworkLink).delete()
        db.query(Device).delete()
        db.commit()

        result = {"scenario": scenario_id, "expected": "FAIL", "findings": [], "conflicts": []}

        if scenario_id == "A":
            # Scenario A: Guest Isolation Violation
            d1 = Device(name="guest-clients", zone="guest", device_type="client", ip_address="192.168.1.10", subnet="192.168.1.0/24", config={"hostname": "guest-clients"})
            d2 = Device(name="main-firewall", zone="core", device_type="firewall", ip_address="10.0.0.1", subnet="10.0.0.0/24",
                       config={"hostname": "main-firewall", "acls": [{"name": "fw-acl", "rules": [{"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}]}]})
            d3 = Device(name="hr-server", zone="hr", device_type="server", ip_address="10.0.1.10", subnet="10.0.1.0/24", config={"hostname": "hr-server"})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id, status="up"),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id, status="up")
            ])
            
            intent = Intent(natural_language="The guest network must not communicate with the HR network", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="deny", source_zone="guest", destination_zone="hr", protocol="ip", port="any", action="deny")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation, "finding_id": f.id} for f in findings]
            
        elif scenario_id == "B":
            # Scenario B: Missing Route Reachability Failure
            d1 = Device(name="eng-clients", zone="eng", device_type="client", ip_address="10.1.5.10", subnet="10.1.5.0/24", config={"hostname": "eng-clients"})
            d2 = Device(name="core-router", zone="core", device_type="router", ip_address="10.0.0.2", subnet="10.0.0.0/24",
                       config={"hostname": "core-router", "routes": [], "acls": [{"name": "core-pass", "rules": [{"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}]}]})
            d3 = Device(name="app-server", zone="app", device_type="server", ip_address="10.1.6.10", subnet="10.1.6.0/24", config={"hostname": "app-server"})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id, status="up"),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id, status="up")
            ])
            
            intent = Intent(natural_language="Engineering devices must be able to access the application server", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="allow", source_zone="eng", destination_zone="app", protocol="ip", port="any", action="permit")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation, "finding_id": f.id} for f in findings]
            
        elif scenario_id == "C":
            # Scenario C: Unauthorized SSH Access
            d1 = Device(name="core-router", zone="core", device_type="router", ip_address="10.0.0.3", subnet="10.0.0.0/24",
                       config={"hostname": "core-router", "acls": [{"name": "vty-acl", "rules": [{"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": "22"}]}]})
            d2 = Device(name="any-client", zone="external", device_type="client", ip_address="8.8.8.8", subnet="8.8.8.0/24", config={"hostname": "any-client"})
            db.add_all([d1, d2])
            db.commit()
            db.add(NetworkLink(source_device_id=d2.id, target_device_id=d1.id, status="up"))
            
            intent = Intent(natural_language="External networks must not access the core router via SSH", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="deny", source_zone="external", destination_zone="core", protocol="tcp", port="22", action="deny")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation, "finding_id": f.id} for f in findings]

        elif scenario_id == "D":
            # Scenario D: Database Exposure
            d1 = Device(name="guest-clients", zone="guest", device_type="client", ip_address="192.168.1.10", subnet="192.168.1.0/24", config={"hostname": "guest-clients"})
            d2 = Device(name="main-firewall", zone="core", device_type="firewall", ip_address="10.0.0.4", subnet="10.0.0.0/24",
                       config={"hostname": "main-firewall", "acls": [{"name": "fw-acl", "rules": [{"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": "3306"}]}]})
            d3 = Device(name="db-server", zone="db", device_type="server", ip_address="10.0.2.10", subnet="10.0.2.0/24", config={"hostname": "db-server"})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id, status="up"),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id, status="up")
            ])
            
            intent = Intent(natural_language="Guest users must not access the database", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="deny", source_zone="guest", destination_zone="db", protocol="tcp", port="3306", action="deny")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation, "finding_id": f.id} for f in findings]

        elif scenario_id == "E":
            # Scenario E: Conflicting Intents
            d1 = Device(name="eng-clients", zone="eng", device_type="client", ip_address="10.1.5.10", subnet="10.1.5.0/24", config={"hostname": "eng-clients"})
            d2 = Device(name="db-server", zone="db", device_type="server", ip_address="10.0.2.10", subnet="10.0.2.0/24", config={"hostname": "db-server"})
            db.add_all([d1, d2])
            db.commit()
            db.add(NetworkLink(source_device_id=d1.id, target_device_id=d2.id, status="up"))

            intent1 = Intent(natural_language="Engineering must reach DB", status="parsed")
            intent2 = Intent(natural_language="No one can reach DB", status="parsed")
            db.add_all([intent1, intent2])
            db.commit()
            
            pol1 = NormalizedPolicy(intent_id=intent1.id, policy_type="allow", source_zone="eng", destination_zone="db", action="permit")
            pol2 = NormalizedPolicy(intent_id=intent2.id, policy_type="deny", source_zone="any", destination_zone="db", action="deny")
            db.add_all([pol1, pol2])
            db.commit()
            
            result["expected"] = "CONFLICT"
            result["conflicts"] = [
                f"Contradictory intents: Policy {pol1.id} (ALLOW: eng -> db) directly contradicts Policy {pol2.id} (DENY: any -> db). Unresolved policy relationship."
            ]
            result["findings"] = [
                {
                    "status": "UNKNOWN",
                    "details": "Verification suspended: conflicting policies detect contradictory security requirements for destination zone 'db'.",
                    "remediation": "Review and resolve contradictory intents before automated deployment."
                }
            ]
            result["repair"] = "REFUSED - conflict must be explicitly resolved by administrator"

        return result
