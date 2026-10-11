from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.repair import RepairProposal
from app.services.repair_engine import RepairEngine
from app.services.audit_service import AuditService

router = APIRouter()

class ProposeRequest(BaseModel):
    finding_id: int

class ValidateRequest(BaseModel):
    repair_id: int

@router.post("/propose", status_code=status.HTTP_201_CREATED)
def propose_repair(req: ProposeRequest, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        proposal = engine.propose_repair(req.finding_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return proposal

@router.post("/validate")
def validate_repair(req: ValidateRequest, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        result = engine.validate_repair(req.repair_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result

@router.post("/{repair_id}/approve")
def approve_repair(repair_id: int, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        engine.apply_repair(repair_id)
        AuditService.log(db, action="APPROVE_REPAIR", entity_type="RepairProposal", entity_id=repair_id, details="Repair applied")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Repair approved and applied"}

@router.post("/{repair_id}/rollback")
def rollback_repair(repair_id: int, db: Session = Depends(get_db)):
    engine = RepairEngine(db)
    try:
        engine.rollback_repair(repair_id)
        AuditService.log(db, action="ROLLBACK_REPAIR", entity_type="RepairProposal", entity_id=repair_id, details="Repair rolled back")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Repair rolled back"}

@router.get("/")
def list_repairs(db: Session = Depends(get_db)):
    return db.query(RepairProposal).all()

@router.get("/{repair_id}")
def get_repair(repair_id: int, db: Session = Depends(get_db)):
    repair = db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair proposal not found")
    return repair
