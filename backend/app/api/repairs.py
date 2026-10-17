from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.models.repair import RepairProposal
from app.services.repair_engine import RepairEngine
from app.services.audit_service import AuditService

router = APIRouter()

class ProposeRequest(BaseModel):
    finding_id: int

class ValidateRequest(BaseModel):
    repair_id: int

def _serialize_repair(r: RepairProposal) -> Dict[str, Any]:
    return {
        "id": r.id,
        "finding_id": r.finding_id,
        "policy_id": r.policy_id,
        "description": r.description,
        "original_config": r.original_config,
        "proposed_config": r.proposed_config,
        "change_type": r.change_type,
        "affected_devices": r.affected_devices or [],
        "expected_result": r.expected_result,
        "validation_status": r.validation_status,
        "approval_status": r.approval_status,
        "approved_by": r.approved_by,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "applied_at": r.applied_at.isoformat() if r.applied_at else None,
        "rolled_back_at": r.rolled_back_at.isoformat() if r.rolled_back_at else None,
        "created_at": r.created_at.isoformat() if hasattr(r, 'created_at') and r.created_at else None
    }

@router.post("/propose", status_code=status.HTTP_201_CREATED)
def propose_repair(req: ProposeRequest, db: Session = Depends(get_db)):
    # Check if a proposal already exists for this finding
    existing = db.query(RepairProposal).filter(RepairProposal.finding_id == req.finding_id).first()
    if existing:
        return _serialize_repair(existing)

    engine = RepairEngine(db)
    try:
        proposal = engine.propose_repair(req.finding_id)
        if not proposal:
            raise HTTPException(status_code=400, detail="Cannot generate repair for this finding (not in FAIL state or no affected device)")
        AuditService.log(db, action="PROPOSE_REPAIR", entity_type="RepairProposal", entity_id=proposal.id, details=proposal.description)
        return _serialize_repair(proposal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate")
def validate_repair(req: ValidateRequest, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        result = engine.validate_repair(req.repair_id)
        repair = db.query(RepairProposal).filter(RepairProposal.id == req.repair_id).first()
        serialized = _serialize_repair(repair) if repair else None
        return {
            **result,
            "repair": serialized
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{repair_id}/approve")
def approve_repair(repair_id: int, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        success = engine.apply_repair(repair_id)
        if not success:
            raise HTTPException(status_code=404, detail="Repair proposal not found")
        AuditService.log(db, action="APPROVE_REPAIR", entity_type="RepairProposal", entity_id=repair_id, details="Repair applied to simulated device")
        repair = db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        return {
            "message": "Repair approved and applied successfully",
            "repair": _serialize_repair(repair)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{repair_id}/rollback")
def rollback_repair(repair_id: int, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        success = engine.rollback_repair(repair_id)
        if not success:
            raise HTTPException(status_code=400, detail="Repair cannot be rolled back (either not applied or not found)")
        AuditService.log(db, action="ROLLBACK_REPAIR", entity_type="RepairProposal", entity_id=repair_id, details="Repair rolled back to previous version")
        repair = db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
        return {
            "message": "Repair rolled back successfully",
            "repair": _serialize_repair(repair)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def list_repairs(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RepairProposal).order_by(RepairProposal.id.desc())
    if status:
        query = query.filter(RepairProposal.approval_status == status)
    repairs = query.all()
    return [_serialize_repair(r) for r in repairs]

@router.get("/{repair_id}")
def get_repair(repair_id: int, db: Session = Depends(get_db)):
    repair = db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair proposal not found")
    return _serialize_repair(repair)

