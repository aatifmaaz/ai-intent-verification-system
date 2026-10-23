from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.intent import Intent, NormalizedPolicy
from app.services.intent_parser import IntentParser
from app.services.llm_parser import LLMIntentParser
from app.services.audit_service import AuditService

router = APIRouter()
intent_parser = IntentParser()
llm_intent_parser = LLMIntentParser(deterministic_parser=intent_parser)


class IntentCreate(BaseModel):
    natural_language: str

class IntentUpdate(BaseModel):
    natural_language: str

def serialize_policy(p: NormalizedPolicy) -> dict:
    return {
        "id": p.id,
        "intent_id": p.intent_id,
        "policy_type": p.policy_type,
        "source_zone": p.source_zone,
        "source_network": p.source_network,
        "destination_zone": p.destination_zone,
        "destination_network": p.destination_network,
        "protocol": p.protocol,
        "port": p.port,
        "action": p.action,
        "priority": p.priority or 100,
        "conditions": p.conditions
    }

def serialize_intent(intent: Intent, policies: List[NormalizedPolicy]) -> dict:
    return {
        "id": intent.id,
        "natural_language": intent.natural_language,
        "status": intent.status,
        "confidence": intent.confidence,
        "assumptions": intent.assumptions,
        "created_at": intent.created_at.isoformat() if intent.created_at else None,
        "updated_at": intent.updated_at.isoformat() if intent.updated_at else None,
        "policies": [serialize_policy(p) for p in policies]
    }

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_intent(intent_in: IntentCreate, db: Session = Depends(get_db)):
    if not intent_in.natural_language or not intent_in.natural_language.strip():
        raise HTTPException(status_code=422, detail="Natural language requirement cannot be empty.")

    parsed_result = llm_intent_parser.parse(intent_in.natural_language, db=db)
    if not parsed_result.get("policies") or parsed_result.get("status") in ["unsupported", "needs_clarification"]:
        raise HTTPException(status_code=422, detail=parsed_result.get("assumptions") or "I couldn't identify a valid network rule in that sentence. Specify source and destination zones or networks.")

    
    new_intent = Intent(
        natural_language=intent_in.natural_language,
        status="parsed",
        confidence=parsed_result.get("confidence", 1.0),
        assumptions=parsed_result.get("assumptions")
    )

    db.add(new_intent)
    db.commit()
    db.refresh(new_intent)
    
    policies = []
    for pol_data in parsed_result.get("policies", []):
        policy = NormalizedPolicy(
            intent_id=new_intent.id,
            policy_type=pol_data.get("policy_type", "allow"),
            source_zone=pol_data.get("source_zone") or pol_data.get("source"),
            source_network=pol_data.get("source_network"),
            destination_zone=pol_data.get("destination_zone") or pol_data.get("destination"),
            destination_network=pol_data.get("destination_network"),
            protocol=pol_data.get("protocol"),
            port=pol_data.get("port"),
            action=pol_data.get("action", "allow")
        )
        db.add(policy)
        policies.append(policy)
    
    db.commit()
    
    AuditService.log(db, action="CREATE_INTENT", entity_type="Intent", entity_id=new_intent.id, details="Intent created and parsed")
    
    return serialize_intent(new_intent, policies)

@router.post("/auto-enforce")
def auto_enforce_intent(intent_in: IntentCreate, db: Session = Depends(get_db)):
    from app.services.verification_engine import VerificationEngine
    from app.services.repair_engine import RepairEngine
    from app.models.verification import VerificationFinding

    # 1. Parse the requested policy against the active topology.
    parsed_result = intent_parser.parse(intent_in.natural_language, db=db)
    if not parsed_result.get("policies"):
        raise HTTPException(status_code=422, detail="I couldn't identify a network rule in that sentence. Specify which network or device should be allowed or blocked from which destination.")

    created_policies = []
    policy_specs = []
    for pol_data in parsed_result.get("policies", []):
        policy_specs.append({
            "policy_type": pol_data.get("policy_type", "allow"),
            "source_zone": pol_data.get("source_zone") or pol_data.get("source"),
            "source_network": pol_data.get("source_network"),
            "destination_zone": pol_data.get("destination_zone") or pol_data.get("destination"),
            "destination_network": pol_data.get("destination_network"),
            "protocol": pol_data.get("protocol"),
            "port": pol_data.get("port"),
            "action": pol_data.get("action", "allow")
        })

    # Re-running an identical command should verify the existing requirement,
    # not create another indistinguishable intent and policy row.
    existing = [db.query(NormalizedPolicy).filter_by(**spec).first() for spec in policy_specs]
    reused_existing = bool(existing) and all(existing)
    if reused_existing:
        created_policies = existing
        new_intent = db.query(Intent).filter_by(id=created_policies[0].intent_id).first()
        reused_existing = new_intent is not None
    if not reused_existing:
        created_policies = []
        new_intent = Intent(
            natural_language=intent_in.natural_language,
            status="parsed",
            confidence=parsed_result.get("confidence", 1.0),
            assumptions=parsed_result.get("assumptions")
        )
        db.add(new_intent)
        db.commit()
        db.refresh(new_intent)
        for spec in policy_specs:
            policy = NormalizedPolicy(intent_id=new_intent.id, **spec)
            db.add(policy)
            created_policies.append(policy)
        db.commit()
        AuditService.log(db, action="CREATE_INTENT", entity_type="Intent", entity_id=new_intent.id, details=f"Auto-pilot initiated for: {new_intent.natural_language}")
    else:
        new_intent.updated_at = datetime.utcnow()
        if new_intent.status == "archived":
            new_intent.status = "parsed"
    if reused_existing:
        AuditService.log(db, action="VERIFY_EXISTING_INTENT", entity_type="Intent", entity_id=new_intent.id, details=f"Repeated command checked existing requirement: {intent_in.natural_language}")

    # The newest explicit command replaces older, directly contradictory
    # requirements with the same endpoints and traffic scope.
    for required in created_policies:
        competing = db.query(NormalizedPolicy).filter_by(
            source_zone=required.source_zone,
            source_network=required.source_network,
            destination_zone=required.destination_zone,
            destination_network=required.destination_network,
            protocol=required.protocol,
            port=required.port
        ).all()
        for previous in competing:
            if previous.id == required.id or previous.action == required.action:
                continue
            previous_intent = db.query(Intent).filter_by(id=previous.intent_id).first()
            if (previous_intent and previous_intent.id != new_intent.id
                    and previous_intent.status != "archived"
                    and (previous_intent.updated_at or previous_intent.created_at) <= new_intent.updated_at):
                previous_intent.status = "archived"
                AuditService.log(
                    db,
                    action="SUPERSEDE_INTENT",
                    entity_type="Intent",
                    entity_id=previous_intent.id,
                    details=f"Superseded by newer policy {required.id} with the same traffic scope"
                )
    db.commit()

    # 3. Initial Graph Verification
    v_engine = VerificationEngine(db)
    initial_run = v_engine.verify()

    # Find findings for the new policy
    policy_ids = [p.id for p in created_policies]
    policy_findings = db.query(VerificationFinding).filter(
        VerificationFinding.run_id == initial_run.id,
        VerificationFinding.policy_id.in_(policy_ids)
    ).all()

    fail_findings = [f for f in policy_findings if f.status == "FAIL"]

    steps = [
        {"step": 1, "status": "completed", "title": "Natural Language Translation", "detail": f"Parsed English input into formal {created_policies[0].policy_type.upper()} policy ({created_policies[0].source_zone} → {created_policies[0].destination_zone})."},
        {"step": 2, "status": "completed", "title": "Graph Reachability Audit", "detail": f"Evaluated network topology. Result: {len(fail_findings)} security violation(s) identified."}
    ]

    # If already compliant
    if not fail_findings:
        is_unknown = any(f.status == "UNKNOWN" for f in policy_findings)
        status_msg = "UNKNOWN" if is_unknown else "COMPLIANT"
        if not is_unknown:
            new_intent.status = "active"
            db.commit()
        steps.append({
            "step": 3,
            "status": "completed",
            "title": "Compliance Determination",
            "detail": "Network graph currently satisfies this requirement; no policy violation was found." if not is_unknown else "Could not verify because the required source or destination endpoint is missing."
        })
        steps.append({
            "step": 4,
            "status": "completed",
            "title": "Policy Validation",
            "detail": "Checked reachability and ACL behavior for the requested endpoints." if not is_unknown else "Validation remains incomplete because one or more endpoints are missing."
        })
        steps.append({
            "step": 5,
            "status": "completed",
            "title": "Deployment Decision",
            "detail": "No configuration change was needed, so no ACL was deployed."
        })
        steps.append({
            "step": 6,
            "status": "failed" if is_unknown else "completed",
            "title": "Closed-Loop Verification",
            "detail": "The live graph verification returned PASS for every requested policy." if not is_unknown else "The live graph could not verify every requested policy."
        })
        return {
            "status": status_msg,
            "intent": {
                "id": new_intent.id,
                "natural_language": new_intent.natural_language,
                "confidence": new_intent.confidence
            },
            "policies": [{"id": p.id, "type": p.policy_type, "source": p.source_zone, "source_network": p.source_network, "dest": p.destination_zone, "destination_network": p.destination_network} for p in created_policies],
            "remediation_applied": False,
            "steps": steps,
            "message": "Verification is incomplete because an endpoint is missing." if is_unknown else ("Requirement verified as compliant. No duplicate policy was created." if reused_existing else "Intent registered and verified as compliant.")
        }

    # 4. Synthesize Minimal Patch
    r_engine = RepairEngine(db)
    target_finding = fail_findings[0]
    proposal = r_engine.propose_repair(target_finding.id)
    
    if not proposal:
        steps.append({"step": 3, "status": "failed", "title": "Remediation Synthesis", "detail": "Unable to synthesize automated patch for this finding."})
        return {
            "status": "FAIL",
            "intent": {"id": new_intent.id, "natural_language": new_intent.natural_language},
            "steps": steps,
            "message": "Violation detected but automated patch could not be generated."
        }

    steps.append({
        "step": 3,
        "status": "completed",
        "title": "Minimal Patch Synthesis",
        "detail": f"Root cause isolated. Generated minimal {proposal.change_type} patch on {', '.join(proposal.affected_devices or [])}."
    })

    # 5. Sandbox Dry-run Validation
    val_result = r_engine.validate_repair(proposal.id)
    if not val_result.get("valid"):
        steps.append({"step": 4, "status": "failed", "title": "Isolated Sandbox Validation", "detail": val_result.get("error", "Patch validation failed.")})
        return {
            "status": "FAIL",
            "intent": {"id": new_intent.id, "natural_language": new_intent.natural_language},
            "policies": [{"id": p.id, "type": p.policy_type, "source": p.source_zone, "source_network": p.source_network, "dest": p.destination_zone, "destination_network": p.destination_network} for p in created_policies],
            "remediation_applied": False,
            "steps": steps,
            "message": "A patch was generated, but sandbox validation failed. No ACL was deployed."
        }
    steps.append({
        "step": 4,
        "status": "completed",
        "title": "Isolated Sandbox Validation",
        "detail": val_result.get("message", "The isolated policy validation passed.")
    })

    # 6. Autonomous Deployment
    if not r_engine.apply_repair(proposal.id):
        steps.append({"step": 5, "status": "failed", "title": "Autonomous Hardware Deployment", "detail": "The ACL patch could not be applied to the target device."})
        return {
            "status": "FAIL",
            "intent": {"id": new_intent.id, "natural_language": new_intent.natural_language},
            "policies": [{"id": p.id, "type": p.policy_type, "source": p.source_zone, "source_network": p.source_network, "dest": p.destination_zone, "destination_network": p.destination_network} for p in created_policies],
            "repair": {"id": proposal.id, "description": proposal.description, "affected_devices": proposal.affected_devices, "original_config": proposal.original_config, "proposed_config": proposal.proposed_config, "change_type": proposal.change_type},
            "remediation_applied": False,
            "steps": steps,
            "message": "The ACL patch could not be deployed."
        }
    AuditService.log(db, action="AUTO_APPLY_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details="Autonomous repair applied via closed-loop auto-enforce")
    steps.append({
        "step": 5,
        "status": "completed",
        "title": "Autonomous Hardware Deployment",
        "detail": f"Injected patch into device configuration and recorded new version in ledger."
    })

    # 7. Closed-Loop Re-verification
    re_run = v_engine.verify()
    final_policy_findings = db.query(VerificationFinding).filter(
        VerificationFinding.run_id == re_run.id,
        VerificationFinding.policy_id.in_(policy_ids)
    ).all()
    all_passing = bool(final_policy_findings) and all(f.status == "PASS" for f in final_policy_findings)

    steps.append({
        "step": 6,
        "status": "completed" if all_passing else "failed",
        "title": "Closed-Loop Verification",
        "detail": "Re-verified network graph reachability: all requested policies pass." if all_passing else "ACL was deployed, but re-verification found a remaining violation."
    })

    remediation_applied = True
    if all_passing:
        new_intent.status = "active"
        db.commit()
    else:
        # Never leave an automatically deployed patch in place if the live
        # graph does not confirm the requested result.
        r_engine.rollback_repair(proposal.id)
        remediation_applied = False
        AuditService.log(db, action="AUTO_ROLLBACK_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details="Automatically rolled back because closed-loop verification did not pass")
        steps.append({
            "step": 7,
            "status": "completed",
            "title": "Automatic Rollback",
            "detail": "Restored the original device configuration after post-deployment verification failed."
        })

    return {
        "status": "REMEDIATED" if all_passing else "FAIL",
        "intent": {
            "id": new_intent.id,
            "natural_language": new_intent.natural_language,
            "confidence": new_intent.confidence
        },
        "policies": [{"id": p.id, "type": p.policy_type, "source": p.source_zone, "source_network": p.source_network, "dest": p.destination_zone, "destination_network": p.destination_network} for p in created_policies],
        "repair": {
            "id": proposal.id,
            "description": proposal.description,
            "affected_devices": proposal.affected_devices,
            "original_config": proposal.original_config,
            "proposed_config": proposal.proposed_config,
            "change_type": proposal.change_type
        },
        "remediation_applied": remediation_applied,
        "steps": steps,
        "initial_run": {"passed": initial_run.passed, "failed": initial_run.failed},
        "final_run": {"passed": re_run.passed, "failed": re_run.failed},
        "message": (f"Successfully auto-enforced intent. Minimal patch applied to {', '.join(proposal.affected_devices or [])} and verified compliant." if all_passing else f"The proposed ACL did not pass closed-loop verification and was rolled back on {', '.join(proposal.affected_devices or [])}.")
    }


@router.get("/")
def list_intents(db: Session = Depends(get_db)):
    intents = db.query(Intent).all()
    results = []
    for intent in intents:
        policies = db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).all()
        results.append(serialize_intent(intent, policies))
    return results

@router.get("/{intent_id}")
def get_intent(intent_id: int, db: Session = Depends(get_db)):
    intent = db.query(Intent).filter(Intent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    policies = db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).all()
    return serialize_intent(intent, policies)

@router.put("/{intent_id}")
def update_intent(intent_id: int, intent_in: IntentUpdate, db: Session = Depends(get_db)):
    intent = db.query(Intent).filter(Intent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    if not intent_in.natural_language or not intent_in.natural_language.strip():
        raise HTTPException(status_code=422, detail="Natural language requirement cannot be empty.")

    intent.natural_language = intent_in.natural_language
    
    # Re-parse
    parsed_result = intent_parser.parse(intent_in.natural_language, db=db)
    if not parsed_result.get("policies"):
        raise HTTPException(status_code=422, detail="I couldn't identify a network rule in that sentence. Specify which network or device should be allowed or blocked from which destination.")
    intent.status = "parsed"
    intent.confidence = parsed_result.get("confidence", 1.0)
    intent.assumptions = parsed_result.get("assumptions")
    
    # Delete old policies
    db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).delete()
    
    policies = []
    for pol_data in parsed_result.get("policies", []):
        policy = NormalizedPolicy(
            intent_id=intent.id,
            policy_type=pol_data.get("policy_type", "allow"),
            source_zone=pol_data.get("source_zone") or pol_data.get("source"),
            source_network=pol_data.get("source_network"),
            destination_zone=pol_data.get("destination_zone") or pol_data.get("destination"),
            destination_network=pol_data.get("destination_network"),
            protocol=pol_data.get("protocol"),
            port=pol_data.get("port"),
            action=pol_data.get("action", "allow")
        )
        db.add(policy)
        policies.append(policy)
        
    db.commit()
    AuditService.log(db, action="UPDATE_INTENT", entity_type="Intent", entity_id=intent.id, details="Intent updated and re-parsed")
    
    return serialize_intent(intent, policies)

@router.delete("/{intent_id}")
def delete_intent(intent_id: int, db: Session = Depends(get_db)):
    intent = db.query(Intent).filter(Intent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).delete()
    db.delete(intent)
    db.commit()
    AuditService.log(db, action="DELETE_INTENT", entity_type="Intent", entity_id=intent_id, details="Intent deleted")
    return {"message": "Intent deleted"}
