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
@router.post("/device", status_code=status.HTTP_201_CREATED)
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


class CustomTopologyImport(BaseModel):
    name: Optional[str] = "Custom Network Topology"
    devices: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    intents: Optional[List[str]] = []

@router.get("/templates")
def list_templates():
    from app.seed.topology_templates import TOPOLOGY_TEMPLATES
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "device_count": len(t["devices"]),
            "link_count": len(t["links"]),
            "sample_intents": t.get("sample_intents", [])
        } for t in TOPOLOGY_TEMPLATES.values()
    ]

@router.post("/templates/{template_id}/load")
def load_template(template_id: str, db: Session = Depends(get_db)):
    import json
    from app.seed.topology_templates import TOPOLOGY_TEMPLATES
    from app.services.verification_engine import VerificationEngine
    from app.services.audit_service import AuditService
    from app.models.verification import VerificationFinding, VerificationRun
    from app.models.repair import RepairProposal
    from app.models.configuration import NetworkConfiguration, ConfigurationVersion
    from app.models.intent import Intent, NormalizedPolicy
    from app.services.intent_parser import IntentParser

    template = TOPOLOGY_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    # Purge old topology & state
    db.query(VerificationFinding).delete()
    db.query(VerificationRun).delete()
    db.query(RepairProposal).delete()
    db.query(ConfigurationVersion).delete()
    db.query(NetworkConfiguration).delete()
    db.query(NormalizedPolicy).delete()
    db.query(Intent).delete()
    db.query(NetworkLink).delete()
    db.query(Device).delete()
    db.commit()

    # Load devices
    dev_objs = {}
    for d_data in template["devices"]:
        dev = Device(**d_data)
        db.add(dev)
        db.flush()
        dev_objs[dev.name] = dev

    # Load links
    for src_name, tgt_name in template["links"]:
        if src_name in dev_objs and tgt_name in dev_objs:
            link = NetworkLink(
                source_device_id=dev_objs[src_name].id,
                target_device_id=dev_objs[tgt_name].id,
                source_interface="eth0",
                target_interface="eth1",
                link_type="ethernet",
                bandwidth="1Gbps",
                status="up"
            )
            db.add(link)
    db.commit()

    # Load initial baseline intents
    intent_parser = IntentParser()
    for sample in template.get("sample_intents", []):
        parsed = intent_parser.parse(sample, fallback_on_unrecognized=True)
        if parsed.get("policies"):
            it = Intent(
                natural_language=sample,
                status="active",
                confidence=parsed.get("confidence", 0.95),
                assumptions=parsed.get("assumptions")
            )
            db.add(it)
            db.flush()
            for p_data in parsed["policies"]:
                p = NormalizedPolicy(
                    intent_id=it.id,
                    policy_type=p_data.get("policy_type", "allow"),
                    source_zone=p_data.get("source_zone"),
                    destination_zone=p_data.get("destination_zone"),
                    protocol=p_data.get("protocol"),
                    port=p_data.get("port"),
                    action=p_data.get("action", "allow")
                )
                db.add(p)
    db.commit()

    # Create baseline device configs
    for dev in db.query(Device).all():
        cfg_data = dev.config or {"hostname": dev.name, "zone": dev.zone, "interfaces": dev.interfaces or {}}
        cfg = NetworkConfiguration(
            device_id=dev.id,
            format="json",
            raw_content=json.dumps(cfg_data, indent=2),
            normalized_content=cfg_data,
            version=1,
            is_active=True
        )
        db.add(cfg)
    db.commit()

    # Run initial verification on the new topology
    v_engine = VerificationEngine(db)
    run = v_engine.verify()

    AuditService.log(db, action="LOAD_TOPOLOGY_TEMPLATE", entity_type="Topology", entity_id=0, details=f"Loaded new topology: {template['name']}")

    return {
        "status": "success",
        "template": template["name"],
        "template_name": template["name"],
        "template_id": template_id,
        "devices_count": len(dev_objs),
        "links_count": len(template["links"]),
        "verification": {
            "passed": run.passed,
            "failed": run.failed,
            "unknown": run.unknown
        },
        "message": f"Successfully loaded '{template['name']}' topology with {len(dev_objs)} devices and {len(template['links'])} links!"
    }

@router.post("/import")
def import_custom_topology(topo_in: CustomTopologyImport, db: Session = Depends(get_db)):
    import json
    from app.services.verification_engine import VerificationEngine
    from app.services.audit_service import AuditService
    from app.models.verification import VerificationFinding, VerificationRun
    from app.models.repair import RepairProposal
    from app.models.configuration import NetworkConfiguration, ConfigurationVersion
    from app.models.intent import Intent, NormalizedPolicy
    from app.services.intent_parser import IntentParser

    if not topo_in.devices:
        raise HTTPException(status_code=400, detail="Custom topology must contain at least 1 device")

    # Purge old topology & state
    db.query(VerificationFinding).delete()
    db.query(VerificationRun).delete()
    db.query(RepairProposal).delete()
    db.query(ConfigurationVersion).delete()
    db.query(NetworkConfiguration).delete()
    db.query(NormalizedPolicy).delete()
    db.query(Intent).delete()
    db.query(NetworkLink).delete()
    db.query(Device).delete()
    db.commit()

    # Add devices
    dev_objs = {}
    for d in topo_in.devices:
        dev = Device(
            name=d.get("name", f"device-{len(dev_objs)+1}"),
            device_type=d.get("device_type", "router"),
            ip_address=d.get("ip_address", "10.0.0.1"),
            subnet=d.get("subnet", "10.0.0.0/24"),
            vlan_id=d.get("vlan_id"),
            zone=d.get("zone", "general"),
            interfaces=d.get("interfaces", {}),
            config=d.get("config", {})
        )
        db.add(dev)
        db.flush()
        dev_objs[dev.name] = dev

    # Add links
    for l in topo_in.links:
        src = l.get("source")
        tgt = l.get("target")
        src_id = l.get("source_device_id") or (dev_objs[src].id if src in dev_objs else None)
        tgt_id = l.get("target_device_id") or (dev_objs[tgt].id if tgt in dev_objs else None)
        if src_id and tgt_id:
            link = NetworkLink(
                source_device_id=src_id,
                target_device_id=tgt_id,
                source_interface=l.get("source_interface", "eth0"),
                target_interface=l.get("target_interface", "eth1"),
                link_type=l.get("link_type", "ethernet"),
                bandwidth=l.get("bandwidth", "1Gbps"),
                status=l.get("status", "up")
            )
            db.add(link)
    db.commit()

    # Add initial intents if any
    intent_parser = IntentParser()
    for sample in (topo_in.intents or []):
        parsed = intent_parser.parse(sample, fallback_on_unrecognized=True)
        if parsed.get("policies"):
            it = Intent(
                natural_language=sample,
                status="active",
                confidence=parsed.get("confidence", 0.95),
                assumptions=parsed.get("assumptions")
            )
            db.add(it)
            db.flush()
            for p_data in parsed["policies"]:
                p = NormalizedPolicy(
                    intent_id=it.id,
                    policy_type=p_data.get("policy_type", "allow"),
                    source_zone=p_data.get("source_zone"),
                    destination_zone=p_data.get("destination_zone"),
                    protocol=p_data.get("protocol"),
                    port=p_data.get("port"),
                    action=p_data.get("action", "allow")
                )
                db.add(p)
    db.commit()

    # Add baseline configs
    for dev in db.query(Device).all():
        cfg_data = dev.config or {"hostname": dev.name, "zone": dev.zone}
        cfg = NetworkConfiguration(
            device_id=dev.id,
            format="json",
            raw_content=json.dumps(cfg_data, indent=2),
            normalized_content=cfg_data,
            version=1,
            is_active=True
        )
        db.add(cfg)
    db.commit()

    v_engine = VerificationEngine(db)
    run = v_engine.verify()

    AuditService.log(db, action="IMPORT_CUSTOM_TOPOLOGY", entity_type="Topology", entity_id=0, details=f"Imported custom topology: {topo_in.name}")

    return {
        "status": "success",
        "name": topo_in.name,
        "devices_count": len(dev_objs),
        "links_count": db.query(NetworkLink).count(),
        "intents_count": len(topo_in.intents or []),
        "verification": {
            "passed": run.passed,
            "failed": run.failed,
            "unknown": run.unknown
        },
        "message": f"Successfully imported '{topo_in.name}' with {len(dev_objs)} devices and {len(topo_in.intents or [])} intents!"
    }


