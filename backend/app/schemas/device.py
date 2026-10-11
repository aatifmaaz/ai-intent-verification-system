from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DeviceBase(BaseModel):
    name: str
    device_type: str
    ip_address: str
    subnet: str
    vlan_id: Optional[int] = None
    zone: Optional[str] = None
    interfaces: Dict[str, Any] = {}
    status: str = "active"

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int
    config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
