from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class VerificationFindingResponse(BaseModel):
    id: int
    run_id: int
    policy_id: int
    status: str
    severity: str
    risk_level: Optional[str] = None
    affected_devices: Optional[Dict[str, Any]] = None
    affected_networks: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class VerificationRunResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_policies: int
    passed: int
    failed: int
    unknown: int
    status: str
    findings: List[VerificationFindingResponse] = []

    model_config = ConfigDict(from_attributes=True)
