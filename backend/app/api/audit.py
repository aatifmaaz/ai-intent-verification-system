from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.models.audit import AuditEvent

router = APIRouter()

@router.get("/")
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    event_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent).order_by(AuditEvent.created_at.desc())
    if event_type and event_type != "ALL":
        query = query.filter(AuditEvent.event_type == event_type)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (AuditEvent.description.ilike(search_pattern)) | 
            (AuditEvent.event_type.ilike(search_pattern))
        )
        
    events = query.limit(limit).all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "description": e.description,
            "user_id": e.user_id,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]

@router.get("/types")
def get_audit_event_types(db: Session = Depends(get_db)):
    types = db.query(AuditEvent.event_type).distinct().all()
    return [t[0] for t in types if t[0]]

