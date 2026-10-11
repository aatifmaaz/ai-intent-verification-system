from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User

router = APIRouter()

# Fixed development API key
DEV_API_KEY = "dev_api_key_123"

class LoginRequest(BaseModel):
    username: str
    password: str

def verify_api_key(request: Request, x_api_key: Optional[str] = Header(None)):
    # Make optional for GET requests
    if request.method == "GET":
        return x_api_key
        
    if x_api_key != DEV_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return x_api_key

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if req.password != "admin":
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        user = User(username=req.username, is_active=True, role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return {
        "api_key": DEV_API_KEY,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }
