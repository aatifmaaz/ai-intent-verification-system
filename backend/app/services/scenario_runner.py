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
            # Guest Isolation
            d1 = Device(name="guest-clients", zone="guest", device_type="host", ip_address="192.168.1.10", config={})
            d2 = Device(name="main-firewall", zone="core", device_type="firewall", ip_address="10.0.0.1", 
                       config={"acls": [{"name": "fw-acl", "rules": [{"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}]}]})
            d3 = Device(name="hr-server", zone="hr", device_type="server", ip_address="10.0.1.10", config={})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id)
            ])
            
            intent = Intent(natural_language="The guest network must not communicate with the HR network", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="deny", source_zone="guest", destination_zone="hr", protocol="ip", port="any")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation} for f in findings]
            
        elif scenario_id == "B":
            # Missing Route (Using allow/require with empty config indicating route issue or just general allow)
            d1 = Device(name="eng-clients", zone="eng", device_type="host", ip_address="10.1.5.10", config={})
            d2 = Device(name="core-router", zone="core", device_type="router", ip_address="10.0.0.2", config={"acls": []}) # No permit means implicitly blocked in our simplistic model
            d3 = Device(name="app-server", zone="app", device_type="server", ip_address="10.1.6.10", config={})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id)
            ])
            
            intent = Intent(natural_language="Engineering devices must be able to access the application server", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="allow", source_zone="eng", destination_zone="app", protocol="ip", port="any")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation} for f in findings]
            
        elif scenario_id == "C":
            # Unauthorized SSH
            d1 = Device(name="core-router", zone="core", device_type="router", ip_address="10.0.0.3", 
                       config={"acls": [{"name": "vty-acl", "rules": [{"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": "22"}]}]})
            d2 = Device(name="any-client", zone="external", device_type="host", ip_address="8.8.8.8", config={})
            db.add_all([d1, d2])
            db.commit()
            db.add(NetworkLink(source_device_id=d2.id, target_device_id=d1.id))
            
            intent = Intent(natural_language="Only administrators may access network devices using SSH", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="restrict", source_zone="admin", destination_zone="core", protocol="tcp", port="22")
            db.add(pol)
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation} for f in findings]

        elif scenario_id == "D":
            # Database Exposure
            d1 = Device(name="guest-clients", zone="guest", device_type="host", ip_address="192.168.1.10", config={})
            d2 = Device(name="fw", zone="core", device_type="firewall", ip_address="10.0.0.4", 
                       config={"acls": [{"name": "fw-acl", "rules": [{"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": "3306"}]}]})
            d3 = Device(name="db-server", zone="db", device_type="server", ip_address="10.0.2.10", config={})
            db.add_all([d1, d2, d3])
            db.commit()
            
            db.add_all([
                NetworkLink(source_device_id=d1.id, target_device_id=d2.id),
                NetworkLink(source_device_id=d2.id, target_device_id=d3.id)
            ])
            
            intent = Intent(natural_language="Database access must remain restricted to the application server", status="parsed")
            db.add(intent)
            db.commit()
            
            pol = NormalizedPolicy(intent_id=intent.id, policy_type="restrict", source_zone="app", destination_zone="db", protocol="tcp", port="3306")
            # And an implicit deny we are checking
            pol2 = NormalizedPolicy(intent_id=intent.id, policy_type="deny", source_zone="guest", destination_zone="db", protocol="tcp", port="3306")
            db.add_all([pol, pol2])
            db.commit()
            
            engine = VerificationEngine(db)
            run = engine.verify()
            findings = db.query(VerificationFinding).filter_by(run_id=run.id).all()
            result["findings"] = [{"status": f.status, "details": f.details, "remediation": f.remediation} for f in findings]

        elif scenario_id == "E":
            # Conflicting Intents
            intent1 = Intent(natural_language="Engineering must reach DB", status="parsed")
            intent2 = Intent(natural_language="No one can reach DB", status="parsed")
            db.add_all([intent1, intent2])
            db.commit()
            
            pol1 = NormalizedPolicy(intent_id=intent1.id, policy_type="allow", source_zone="eng", destination_zone="db")
            pol2 = NormalizedPolicy(intent_id=intent2.id, policy_type="deny", source_zone="any", destination_zone="db")
            db.add_all([pol1, pol2])
            db.commit()
            
            # Simple conflict detection simulation
            result["expected"] = "CONFLICT"
            result["conflicts"] = ["Intent 1 allows eng -> db, Intent 2 denies any -> db"]
            result["repair"] = "REFUSED - conflict must be manually resolved"

        return result
