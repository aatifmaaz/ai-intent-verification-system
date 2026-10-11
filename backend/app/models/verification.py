from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from ..database import Base

class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_policies = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    unknown = Column(Integer, default=0)
    status = Column(String, default="running") # running/completed/failed

class VerificationFinding(Base):
    __tablename__ = "verification_findings"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, index=True)
    policy_id = Column(Integer, index=True)
    status = Column(String) # PASS/FAIL/UNKNOWN
    severity = Column(String) # critical/high/medium/low/info
    risk_level = Column(String, nullable=True)
    affected_devices = Column(JSON, nullable=True)
    affected_networks = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    remediation = Column(String, nullable=True)
    details = Column(String, nullable=True)
