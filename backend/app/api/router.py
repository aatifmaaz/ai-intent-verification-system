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

@api_router.get("/system/status", tags=["System"])
def get_system_status(db: Session = Depends(get_db)):
    from app.models.device import Device
    from app.models.intent import Intent
    from app.models.network_link import NetworkLink
    from app.models.verification import VerificationRun
    from app.models.repair import RepairProposal
    from app.models.configuration import NetworkConfiguration

    device_count = db.query(Device).count()
    link_count = db.query(NetworkLink).count()
    intent_count = db.query(Intent).count()
    config_count = db.query(NetworkConfiguration).count()
    last_run = db.query(VerificationRun).order_by(VerificationRun.started_at.desc()).first()
    pending_repairs = db.query(RepairProposal).filter(RepairProposal.approval_status == "pending").count()

    return {
        "status": "healthy",
        "engine_version": "2.4.0-simulation",
        "mode": "Deterministic Graph + NLP",
        "devices_count": device_count,
        "links_count": link_count,
        "intents_count": intent_count,
        "configurations_count": config_count,
        "pending_repairs": pending_repairs,
        "last_verification": {
            "id": last_run.id if last_run else None,
            "status": last_run.status if last_run else "never_run",
            "passed": last_run.passed if last_run else 0,
            "failed": last_run.failed if last_run else 0,
            "unknown": last_run.unknown if last_run else 0,
            "completed_at": last_run.completed_at.isoformat() if last_run and last_run.completed_at else None
        } if last_run else None
    }


