from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal, init_db
from app.api.router import api_router
from app.seed.seed_data import seed_db
from contextlib import asynccontextmanager

from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(engine)
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    yield

app = FastAPI(title="Network Intent Verification API", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if not origins:
    origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "title": "AI-Driven Network Intent Verification and Automated Configuration Repair",
        "status": "online",
        "mode": "Simulation Engine + NLP",
        "docs_url": "http://127.0.0.1:8000/docs",
        "frontend_url": "http://localhost:3000",
        "health_endpoint": "/health",
        "api_prefix": "/api"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

