from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class IntentBase(BaseModel):
    natural_language: str

class IntentCreate(IntentBase):
    pass

class NormalizedPolicyResponse(BaseModel):
    id: int
    intent_id: int
    policy_type: str
    source_zone: Optional[str] = None
    source_network: Optional[str] = None
    destination_zone: Optional[str] = None
    destination_network: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[str] = None
    action: str
    priority: int
    conditions: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class IntentResponse(IntentBase):
    id: int
    status: str
    confidence: Optional[float] = None
    assumptions: Optional[Dict[str, Any]] = None
    interpreter: Optional[str] = "deterministic"
    parser_provenance: Optional[str] = "deterministic"
    created_at: datetime
    updated_at: datetime
    policies: List[NormalizedPolicyResponse] = []

    model_config = ConfigDict(from_attributes=True)
