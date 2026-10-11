from sqlalchemy import Column, Integer, String, Float
from ..database import Base

class NetworkLink(Base):
    __tablename__ = "network_links"

    id = Column(Integer, primary_key=True, index=True)
    source_device_id = Column(Integer, index=True)
    target_device_id = Column(Integer, index=True)
    source_interface = Column(String)
    target_interface = Column(String)
    link_type = Column(String)
    bandwidth = Column(String, nullable=True)
    status = Column(String, default="up")
