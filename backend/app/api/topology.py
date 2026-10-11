from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.device import Device
from app.models.network_link import NetworkLink
from app.models.intent import NormalizedPolicy
from app.models.verification import VerificationRun
from app.models.repair import RepairProposal

router = APIRouter()

class DeviceCreate(BaseModel):
    name: str
    device_type: str
    ip_address: Optional[str] = None
    subnet: Optional[str] = None
    vlan_id: Optional[int] = None
    zone: Optional[str] = None
    interfaces: Optional[Dict] = None
    status: Optional[str] = "active"
    config: Optional[Dict] = None

class LinkCreate(BaseModel):
    source_device_id: int
    target_device_id: int
    source_interface: str
    target_interface: str
    link_type: Optional[str] = "ethernet"
    bandwidth: Optional[str] = "1G"
    status: Optional[str] = "up"

@router.get("/")
def get_topology(db: Session = Depends(get_db)):
    devices = db.query(Device).all()
    links = db.query(NetworkLink).all()
    
    return {
        "devices": [
            {
                "id": d.id, "name": d.name, "device_type": d.device_type,
                "ip_address": d.ip_address, "subnet": d.subnet, "vlan_id": d.vlan_id,
                "zone": d.zone, "interfaces": d.interfaces, "status": d.status, "config": d.config
            } for d in devices
        ],
        "links": [
            {
                "id": l.id, "source_device_id": l.source_device_id, "target_device_id": l.target_device_id,
                "source_interface": l.source_interface, "target_interface": l.target_interface,
                "link_type": l.link_type, "bandwidth": l.bandwidth, "status": l.status
            } for l in links
        ]
    }

@router.post("/devices", status_code=status.HTTP_201_CREATED)
def create_device(device_in: DeviceCreate, db: Session = Depends(get_db)):
    device = Device(**device_in.dict())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

@router.put("/devices/{device_id}")
def update_device(device_id: int, device_in: DeviceCreate, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    for k, v in device_in.dict().items():
        setattr(device, k, v)
    
    db.commit()
    db.refresh(device)
    return device

@router.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.query(NetworkLink).filter((NetworkLink.source_device_id == device_id) | (NetworkLink.target_device_id == device_id)).delete()
    db.delete(device)
    db.commit()
    return {"message": "Device and its links deleted"}

@router.post("/links", status_code=status.HTTP_201_CREATED)
def create_link(link_in: LinkCreate, db: Session = Depends(get_db)):
    link = NetworkLink(**link_in.dict())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link

@router.delete("/links/{link_id}")
def delete_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(NetworkLink).filter(NetworkLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    db.delete(link)
    db.commit()
    return {"message": "Link deleted"}

@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total_devices = db.query(Device).count()
    total_policies = db.query(NormalizedPolicy).count()
    
    latest_run = db.query(VerificationRun).order_by(VerificationRun.started_at.desc()).first()
    passed = 0
    failed = 0
    unknown = 0
    
    if latest_run:
        passed = latest_run.passed or 0
        failed = latest_run.failed or 0
        unknown = latest_run.unknown or 0
        
    pending_repairs = db.query(RepairProposal).filter(RepairProposal.approval_status == "pending").count()
    
    return {
        "total_devices": total_devices,
        "total_policies": total_policies,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "pending_repairs": pending_repairs
    }

