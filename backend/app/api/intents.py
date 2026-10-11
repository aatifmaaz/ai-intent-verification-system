from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.intent import Intent, NormalizedPolicy
from app.services.intent_parser import IntentParser
from app.services.audit_service import AuditService

router = APIRouter()
intent_parser = IntentParser()

class IntentCreate(BaseModel):
    natural_language: str

class IntentUpdate(BaseModel):
    natural_language: str

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_intent(intent_in: IntentCreate, db: Session = Depends(get_db)):
    parsed_result = intent_parser.parse(intent_in.natural_language)
    
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
            source=pol_data.get("source"),
            destination=pol_data.get("destination"),
            protocol=pol_data.get("protocol"),
            port=pol_data.get("port"),
            action=pol_data.get("action", "allow")
        )
        db.add(policy)
        policies.append(policy)
    
    db.commit()
    
    AuditService.log(db, action="CREATE_INTENT", entity_type="Intent", entity_id=new_intent.id, details="Intent created and parsed")
    
    response = {
        "id": new_intent.id,
        "natural_language": new_intent.natural_language,
        "status": new_intent.status,
        "confidence": new_intent.confidence,
        "assumptions": new_intent.assumptions,
        "created_at": new_intent.created_at,
        "updated_at": new_intent.updated_at,
        "policies": [{"id": p.id, "intent_id": p.intent_id, "policy_type": p.policy_type} for p in policies]
    }
    return response

@router.get("/")
def list_intents(db: Session = Depends(get_db)):
    intents = db.query(Intent).all()
    results = []
    for intent in intents:
        policies = db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).all()
        intent_dict = {
            "id": intent.id,
            "natural_language": intent.natural_language,
            "status": intent.status,
            "confidence": intent.confidence,
            "assumptions": intent.assumptions,
            "created_at": intent.created_at,
            "updated_at": intent.updated_at,
            "policies": [{"id": p.id, "intent_id": p.intent_id, "policy_type": p.policy_type} for p in policies]
        }
        results.append(intent_dict)
    return results

@router.get("/{intent_id}")
def get_intent(intent_id: int, db: Session = Depends(get_db)):
    intent = db.query(Intent).filter(Intent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    policies = db.query(NormalizedPolicy).filter(NormalizedPolicy.intent_id == intent.id).all()
    return {
        "id": intent.id,
        "natural_language": intent.natural_language,
        "status": intent.status,
        "confidence": intent.confidence,
        "assumptions": intent.assumptions,
        "created_at": intent.created_at,
        "updated_at": intent.updated_at,
        "policies": [{"id": p.id, "intent_id": p.intent_id, "policy_type": p.policy_type} for p in policies]
    }

@router.put("/{intent_id}")
def update_intent(intent_id: int, intent_in: IntentUpdate, db: Session = Depends(get_db)):
    intent = db.query(Intent).filter(Intent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    intent.natural_language = intent_in.natural_language
    
    # Re-parse
    parsed_result = intent_parser.parse(intent.natural_language)
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
            source=pol_data.get("source"),
            destination=pol_data.get("destination"),
            protocol=pol_data.get("protocol"),
            port=pol_data.get("port"),
            action=pol_data.get("action", "allow")
        )
        db.add(policy)
        policies.append(policy)
        
    db.commit()
    AuditService.log(db, action="UPDATE_INTENT", entity_type="Intent", entity_id=intent.id, details="Intent updated and re-parsed")
    
    return {
        "id": intent.id,
        "natural_language": intent.natural_language,
        "status": intent.status,
        "confidence": intent.confidence,
        "assumptions": intent.assumptions,
        "created_at": intent.created_at,
        "updated_at": intent.updated_at,
        "policies": [{"id": p.id, "intent_id": p.intent_id, "policy_type": p.policy_type} for p in policies]
    }

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
