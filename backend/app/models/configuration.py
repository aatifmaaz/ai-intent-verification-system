from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean
from ..database import Base, utc_now

class NetworkConfiguration(Base):
    __tablename__ = "network_configurations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)
    format = Column(String) # json/yaml/ios
    raw_content = Column(String)
    normalized_content = Column(JSON)
    version = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)
    version_number = Column(Integer)
    config_data = Column(JSON)
    change_description = Column(String)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
