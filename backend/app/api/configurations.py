from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.database import get_db
from app.models.configuration import NetworkConfiguration
from app.services.config_parser import ConfigParser

router = APIRouter()
config_parser = ConfigParser()

class ConfigImport(BaseModel):
    device_id: int
    format: str
    content: str

@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_configuration(config_in: ConfigImport, db: Session = Depends(get_db)):
    if config_in.format not in ["json", "yaml", "ios"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be json, yaml, or ios.")
    
    try:
        parsed_data = config_parser.parse(config_in.content, format=config_in.format)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse configuration: {str(e)}")
        
    new_config = NetworkConfiguration(
        device_id=config_in.device_id,
        raw_content=config_in.content,
        format=config_in.format,
        parsed_data=parsed_data
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return {
        "id": new_config.id,
        "device_id": new_config.device_id,
        "format": new_config.format,
        "parsed_data": new_config.parsed_data
    }

@router.get("/")
def list_configurations(db: Session = Depends(get_db)):
    configs = db.query(NetworkConfiguration).all()
    return configs

@router.get("/{config_id}")
def get_configuration(config_id: int, db: Session = Depends(get_db)):
    config = db.query(NetworkConfiguration).filter(NetworkConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config
