from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from typing import Dict, Any, List
from app.database import Base, get_db
from app.services.scenario_runner import ScenarioRunner
from app.services.audit_service import AuditService
from app.models.device import Device
from app.models.intent import Intent

router = APIRouter()

SCENARIO_METADATA = [
    {
        "id": "A",
        "name": "Guest Isolation Violation",
        "category": "Zero-Trust Segmentation",
        "severity": "CRITICAL",
        "description": "Guest network can reach HR server. An overly permissive firewall ACL ('permit ip any any') exposes sensitive employee records.",
        "affected_zones": ["guest", "core", "hr"],
        "target_devices": ["guest-clients", "main-firewall", "hr-server"],
        "expected_result": "FAIL",
        "attack_vector": "Lateral movement from untrusted guest WiFi subnet 192.168.1.0/24 into HR subnet 10.0.1.0/24"
    },
    {
        "id": "B",
        "name": "Missing Route Reachability Failure",
        "category": "Routing & Reachability",
        "severity": "HIGH",
        "description": "Engineering workstations cannot communicate with the critical application server due to a missing routing path or dropped packets.",
        "affected_zones": ["eng", "core", "app"],
        "target_devices": ["eng-clients", "core-router", "app-server"],
        "expected_result": "FAIL",
        "attack_vector": "Work disruption - engineering subnet 10.1.5.0/24 isolated from application services"
    },
    {
        "id": "C",
        "name": "Unauthorized SSH Access",
        "category": "Management Plane Security",
        "severity": "CRITICAL",
        "description": "Core router exposes SSH port 22 to non-administrative/external networks instead of restricting access strictly to Admin jump hosts.",
        "affected_zones": ["external", "core"],
        "target_devices": ["any-client", "core-router"],
        "expected_result": "FAIL",
        "attack_vector": "Remote administrative compromise via open management plane interface from 8.8.8.8"
    },
    {
        "id": "D",
        "name": "Production Database Exposure",
        "category": "Data Protection",
        "severity": "CRITICAL",
        "description": "Internal database server is reachable from the guest network without intermediary application tier authorization.",
        "affected_zones": ["guest", "core", "database"],
        "target_devices": ["guest-clients", "core-router", "db-server"],
        "expected_result": "FAIL",
        "attack_vector": "Direct database query exfiltration from unauthenticated guest VLAN"
    },
    {
        "id": "E",
        "name": "Conflicting Intent Policies",
        "category": "Policy Conflict Resolution",
        "severity": "HIGH",
        "description": "Two contradictory network policies exist simultaneously: Engineering must reach DB (ALLOW) vs No one can reach DB (DENY any->db), creating security ambiguity.",
        "affected_zones": ["eng", "core", "database"],
        "target_devices": ["eng-clients", "db-server"],
        "expected_result": "CONFLICT",
        "attack_vector": "Contradictory security requirements creating ambiguous and dangerous policy indeterminacy"
    }
]

@router.get("/")
def list_scenarios(db: Session = Depends(get_db)):
    return SCENARIO_METADATA

@router.post("/{scenario_id}/run")
def run_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scenario_id = scenario_id.upper()
    simulation_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    simulation_db = None
    try:
        # ScenarioRunner builds a sample network by clearing and repopulating
        # its session. Give it a throwaway database so a demo run cannot erase
        # the user's live topology, policies, or verification findings.
        Base.metadata.create_all(bind=simulation_engine)
        SimulationSession = sessionmaker(autocommit=False, autoflush=False, bind=simulation_engine)
        simulation_db = SimulationSession()
        results = ScenarioRunner(simulation_db).run_scenario(scenario_id)
        AuditService.log(
            db,
            action="RUN_SCENARIO",
            entity_type="Scenario",
            entity_id=0,
            details=f"Demo Scenario {scenario_id} initiated and executed"
        )
        # Find metadata
        meta = next((s for s in SCENARIO_METADATA if s["id"] == scenario_id), None)
        return {
            "scenario_id": scenario_id,
            "scenario": meta,
            **results
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if simulation_db is not None:
            simulation_db.close()
        simulation_engine.dispose()

@router.post("/reset/baseline")
def reset_baseline_topology(db: Session = Depends(get_db)):
    from app.seed.seed_data import reset_demo_data
    try:
        reset_demo_data(db)
        AuditService.log(
            db,
            action="RESET_TOPOLOGY",
            entity_type="System",
            entity_id=0,
            details="Network topology and policies reset to full 15-device baseline"
        )
        device_count = db.query(Device).count()
        intent_count = db.query(Intent).count()
        return {
            "success": True,
            "message": f"Topology reset successfully: {device_count} devices and {intent_count} intents restored."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset topology: {str(e)}")

