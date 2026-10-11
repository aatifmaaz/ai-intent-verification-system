from fastapi import APIRouter
from .intents import router as intents_router
from .topology import router as topology_router
from .configurations import router as configurations_router
from .verification import router as verification_router
from .repairs import router as repairs_router
from .scenarios import router as scenarios_router
from .audit import router as audit_router
from .auth import router as auth_router

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from .topology import dashboard_stats

api_router = APIRouter()
api_router.include_router(intents_router, prefix="/intents", tags=["Intents"])
api_router.include_router(topology_router, prefix="/topology", tags=["Topology"])
api_router.include_router(configurations_router, prefix="/configurations", tags=["Configurations"])
api_router.include_router(verification_router, prefix="/verification", tags=["Verification"])
api_router.include_router(repairs_router, prefix="/repairs", tags=["Repairs"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(audit_router, prefix="/audit-logs", tags=["Audit"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])

@api_router.get("/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    return dashboard_stats(db)

