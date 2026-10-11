from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.models.verification import VerificationRun, VerificationFinding
from app.services.verification_engine import VerificationEngine
from app.services.audit_service import AuditService

router = APIRouter()

def _serialize_run(run: VerificationRun, findings: List[VerificationFinding]) -> Dict[str, Any]:
    return {
        "id": run.id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_policies": run.total_policies,
        "passed": run.passed,
        "failed": run.failed,
        "unknown": run.unknown,
        "status": run.status,
        "findings": [
            {
                "id": f.id,
                "run_id": f.run_id,
                "policy_id": f.policy_id,
                "status": f.status,
                "severity": f.severity,
                "risk_level": f.risk_level,
                "affected_devices": f.affected_devices or [],
                "affected_networks": f.affected_networks or [],
                "evidence": f.evidence or {},
                "remediation": f.remediation,
                "details": f.details
            }
            for f in findings
        ]
    }

@router.post("/run", status_code=status.HTTP_201_CREATED)
def run_verification(db: Session = Depends(get_db)):
    engine = VerificationEngine(db)
    run = engine.verify()
    
    findings = db.query(VerificationFinding).filter(VerificationFinding.run_id == run.id).all()
    
    AuditService.log(
        db,
        action="VERIFICATION_RUN",
        entity_type="VerificationRun",
        entity_id=run.id,
        details=f"Verification completed: {run.passed} passed, {run.failed} failed, {run.unknown} unknown"
    )
    
    return _serialize_run(run, findings)

@router.get("/results")
def list_verification_runs(db: Session = Depends(get_db)):
    runs = db.query(VerificationRun).order_by(VerificationRun.started_at.desc()).all()
    result = []
    for r in runs:
        findings = db.query(VerificationFinding).filter(VerificationFinding.run_id == r.id).all()
        result.append(_serialize_run(r, findings))
    return result

@router.get("/results/{run_id}")
def get_verification_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(VerificationRun).filter(VerificationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Verification run not found")
        
    findings = db.query(VerificationFinding).filter(VerificationFinding.run_id == run.id).all()
    return _serialize_run(run, findings)

@router.get("/results/{run_id}/findings")
def get_run_findings(run_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(VerificationFinding).filter(VerificationFinding.run_id == run_id)
    if status:
        query = query.filter(VerificationFinding.status == status)
        
    findings = query.all()
    return [
        {
            "id": f.id,
            "run_id": f.run_id,
            "policy_id": f.policy_id,
            "status": f.status,
            "severity": f.severity,
            "risk_level": f.risk_level,
            "affected_devices": f.affected_devices or [],
            "affected_networks": f.affected_networks or [],
            "evidence": f.evidence or {},
            "remediation": f.remediation,
            "details": f.details
        }
        for f in findings
    ]
