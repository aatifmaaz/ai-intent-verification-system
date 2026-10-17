from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.database import get_db
from app.models.configuration import NetworkConfiguration, ConfigurationVersion
from app.models.device import Device
from app.services.config_parser import ConfigParser
from app.services.audit_service import AuditService

router = APIRouter()
config_parser = ConfigParser()

class ConfigImport(BaseModel):
    device_id: int
    format: str
    content: str

class ConfigValidate(BaseModel):
    format: str
    content: str

def _serialize_config(c: NetworkConfiguration) -> Dict[str, Any]:
    return {
        "id": c.id,
        "device_id": c.device_id,
        "format": c.format,
        "raw_content": c.raw_content,
        "normalized_content": c.normalized_content,
        "version": c.version or 1,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None
    }

@router.post("/validate")
def validate_configuration(config_in: ConfigValidate):
    if config_in.format not in ["json", "yaml", "ios"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be json, yaml, or ios.")
    try:
        parsed_data = config_parser.parse(config_in.content, format=config_in.format)
        return {
            "valid": True,
            "format": config_in.format,
            "parsed": parsed_data,
            "message": "Configuration successfully validated."
        }
    except Exception as e:
        return {
            "valid": False,
            "format": config_in.format,
            "error": str(e),
            "message": f"Syntax/parse error: {str(e)}"
        }

@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_configuration(config_in: ConfigImport, db: Session = Depends(get_db)):
    if config_in.format not in ["json", "yaml", "ios"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be json, yaml, or ios.")
    
    device = db.query(Device).filter(Device.id == config_in.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device with ID {config_in.device_id} not found")

    try:
        parsed_data = config_parser.parse(config_in.content, format=config_in.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse configuration: {str(e)}")
        
    # Get current version count
    current_version = db.query(ConfigurationVersion).filter(ConfigurationVersion.device_id == device.id).count()
    new_version_num = current_version + 1

    # Archive previous active configs
    db.query(NetworkConfiguration).filter(
        NetworkConfiguration.device_id == device.id,
        NetworkConfiguration.is_active == True
    ).update({"is_active": False})

    new_config = NetworkConfiguration(
        device_id=config_in.device_id,
        raw_content=config_in.content,
        format=config_in.format,
        normalized_content=parsed_data,
        version=new_version_num,
        is_active=True
    )
    db.add(new_config)

    # Save to ConfigurationVersion history
    version_entry = ConfigurationVersion(
        device_id=device.id,
        version_number=new_version_num,
        config_data=parsed_data,
        change_description=f"Imported configuration in {config_in.format} format"
    )
    db.add(version_entry)

    # Synchronize device.config with the parsed data
    device.config = parsed_data
    db.commit()
    db.refresh(new_config)
    
    AuditService.log(
        db,
        action="IMPORT_CONFIGURATION",
        entity_type="Device",
        entity_id=device.id,
        details=f"Configuration v{new_version_num} imported for {device.name} ({config_in.format})"
    )

    return _serialize_config(new_config)

@router.get("/")
def list_configurations(db: Session = Depends(get_db)):
    configs = db.query(NetworkConfiguration).order_by(NetworkConfiguration.created_at.desc()).all()
    return [_serialize_config(c) for c in configs]

@router.get("/device/{device_id}")
def get_device_configurations(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    configs = db.query(NetworkConfiguration).filter(
        NetworkConfiguration.device_id == device_id
    ).order_by(NetworkConfiguration.created_at.desc()).all()
    
    versions = db.query(ConfigurationVersion).filter(
        ConfigurationVersion.device_id == device_id
    ).order_by(ConfigurationVersion.version_number.desc()).all()

    return {
        "device_id": device.id,
        "device_name": device.name,
        "device_type": device.device_type,
        "current_config": device.config,
        "active_configuration": _serialize_config(configs[0]) if configs else None,
        "history": [_serialize_config(c) for c in configs],
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "change_description": v.change_description,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "config_data": v.config_data
            } for v in versions
        ]
    }

@router.get("/{config_id}")
def get_configuration(config_id: int, db: Session = Depends(get_db)):
    config = db.query(NetworkConfiguration).filter(NetworkConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return _serialize_config(config)

