from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String) # admin/operator/viewer
    created_at = Column(DateTime, default=datetime.utcnow)
