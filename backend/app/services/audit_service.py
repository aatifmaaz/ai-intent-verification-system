from datetime import datetime
from app.models import AuditEvent
import json

class AuditService:
    @staticmethod
    def log_event(db, event_type, description, user_id=None, details=None):
        event = AuditEvent(
            event_type=event_type,
            description=description,
            user_id=user_id,
            details=details if details else {},
            created_at=datetime.utcnow()
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def log(db, action=None, entity_type=None, entity_id=None, details=None, description=None, user_id=None):
        event_type = action or entity_type or "audit_event"
        desc = description or f"{event_type} on {entity_type or 'entity'} #{entity_id}: {details or ''}"
        detail_dict = {"entity_type": entity_type, "entity_id": entity_id, "info": details} if not isinstance(details, dict) else details
        return AuditService.log_event(db, event_type=event_type, description=desc, user_id=user_id, details=detail_dict)

    @staticmethod
    def get_events(db, limit=50, event_type=None):
        query = db.query(AuditEvent)
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)
        return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
