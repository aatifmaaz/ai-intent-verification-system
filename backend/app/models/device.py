from sqlalchemy import Column, Integer, String, JSON
from ..database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    device_type = Column(String) # router/switch/firewall/server/client
    ip_address = Column(String)
    subnet = Column(String)
    vlan_id = Column(Integer, nullable=True)
    zone = Column(String, nullable=True)
    interfaces = Column(JSON)
    status = Column(String, default="active")
    config = Column(JSON, nullable=True)
