from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from ..database import Base

class RepairProposal(Base):
    __tablename__ = "repair_proposals"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, index=True)
    policy_id = Column(Integer, index=True)
    description = Column(String)
    original_config = Column(JSON)
    proposed_config = Column(JSON)
    change_type = Column(String)
    affected_devices = Column(JSON)
    expected_result = Column(String)
    validation_status = Column(String, default="pending")
    approval_status = Column(String, default="pending") # pending/approved/rejected/rolled_back
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
