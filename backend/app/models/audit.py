from sqlalchemy import Column, Integer, String, JSON, DateTime
from ..database import Base, utc_now

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    description = Column(String)
    user_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
