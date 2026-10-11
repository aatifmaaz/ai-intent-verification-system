from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from datetime import datetime
from ..database import Base

class Intent(Base):
    __tablename__ = "intents"

    id = Column(Integer, primary_key=True, index=True)
    natural_language = Column(String)
    status = Column(String, default="draft") # draft/parsed/active/archived
    confidence = Column(Float)
    assumptions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NormalizedPolicy(Base):
    __tablename__ = "normalized_policies"

    id = Column(Integer, primary_key=True, index=True)
    intent_id = Column(Integer, index=True)
    policy_type = Column(String) # allow/deny/require/isolate
    source_zone = Column(String, nullable=True)
    source_network = Column(String, nullable=True)
    destination_zone = Column(String, nullable=True)
    destination_network = Column(String, nullable=True)
    protocol = Column(String, nullable=True)
    port = Column(String, nullable=True)
    action = Column(String)
    priority = Column(Integer, default=100)
    conditions = Column(JSON, nullable=True)
