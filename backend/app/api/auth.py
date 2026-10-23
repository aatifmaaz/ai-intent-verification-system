from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.config import settings

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

def verify_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    # Make optional for GET requests in dev/simulation mode
    if request.method == "GET":
        return x_api_key
        
    expected_key = settings.api_key or "dev_api_key_123"
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return x_api_key

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    expected_password = settings.admin_password or "admin"
    if req.password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        user = User(username=req.username, is_active=True, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return {
        "api_key": settings.api_key,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

