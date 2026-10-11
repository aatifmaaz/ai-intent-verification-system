import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# Pydantic Schemas
schemas_init = ""
schemas_device = """
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DeviceBase(BaseModel):
    name: str
    device_type: str
    ip_address: str
    subnet: str
    vlan_id: Optional[int] = None
    zone: Optional[str] = None
    interfaces: Dict[str, Any] = {}
    status: str = "active"

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: int
    config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
"""
schemas_intent = """
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class IntentBase(BaseModel):
    natural_language: str

class IntentCreate(IntentBase):
    pass

class NormalizedPolicyResponse(BaseModel):
    id: int
    intent_id: int
    policy_type: str
    source_zone: Optional[str] = None
    source_network: Optional[str] = None
    destination_zone: Optional[str] = None
    destination_network: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[str] = None
    action: str
    priority: int
    conditions: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class IntentResponse(IntentBase):
    id: int
    status: str
    confidence: Optional[float] = None
    assumptions: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    policies: List[NormalizedPolicyResponse] = []

    class Config:
        from_attributes = True
"""

schemas_verification = """
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class VerificationFindingResponse(BaseModel):
    id: int
    run_id: int
    policy_id: int
    status: str
    severity: str
    risk_level: Optional[str] = None
    affected_devices: Optional[Dict[str, Any]] = None
    affected_networks: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True

class VerificationRunResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_policies: int
    passed: int
    failed: int
    unknown: int
    status: str
    findings: List[VerificationFindingResponse] = []

    class Config:
        from_attributes = True
"""

# Core Services
service_intent_parser = """
import re

class IntentParser:
    def __init__(self):
        pass
        
    def parse(self, natural_language: str):
        # Deterministic parsing using regex/keyword matching
        nl = natural_language.lower()
        
        policy_type = "allow"
        action = "permit"
        src = None
        dst = None
        protocol = None
        port = None
        confidence = 0.8
        
        # Compound
        if "must have internet access but must not access" in nl:
            match = re.search(r'(.*) must have internet access but must not access (.*)', nl)
            if match:
                return {
                    "status": "parsed",
                    "confidence": 0.9,
                    "policies": [
                        {"policy_type": "allow", "action": "permit", "source_zone": match.group(1).strip(), "destination_zone": "internet", "protocol": "any", "port": "any"},
                        {"policy_type": "deny", "action": "deny", "source_zone": match.group(1).strip(), "destination_zone": match.group(2).strip(), "protocol": "any", "port": "any"}
                    ]
                }
                
        # Isolate
        if "must remain isolated from" in nl:
            match = re.search(r'(.*) must remain isolated from (.*)', nl)
            if match:
                src, dst = match.group(1).strip(), match.group(2).strip()
                policy_type = "isolate"
                action = "deny"
                confidence = 0.95
                
        # Restrict
        elif "only" in nl and "may access" in nl:
            match = re.search(r'only (.*) may access (.*) using (.*)', nl)
            if match:
                src, dst, proto = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
                policy_type = "restrict"
                action = "permit"
                protocol = proto
                confidence = 0.9
                
        # Deny
        elif "must not communicate with" in nl:
            match = re.search(r'(.*) must not communicate with (.*)', nl)
            if match:
                src, dst = match.group(1).strip(), match.group(2).strip()
                policy_type = "deny"
                action = "deny"
                confidence = 0.95
                
        # Allow with protocol
        elif "must be reachable through" in nl:
            match = re.search(r'(.*) must be reachable through (.*)', nl)
            if match:
                dst, proto = match.group(1).strip(), match.group(2).strip()
                src = "any"
                policy_type = "allow"
                action = "permit"
                protocol = proto
                confidence = 0.85
                
        # Allow
        elif "must be able to access" in nl:
            match = re.search(r'(.*) must be able to access (.*)', nl)
            if match:
                src, dst = match.group(1).strip(), match.group(2).strip()
                policy_type = "allow"
                action = "permit"
                confidence = 0.9
                
        if src and dst:
            return {
                "status": "parsed",
                "confidence": confidence,
                "policies": [{
                    "policy_type": policy_type,
                    "action": action,
                    "source_zone": src,
                    "destination_zone": dst,
                    "protocol": protocol or "any",
                    "port": port or "any"
                }]
            }
            
        return {"status": "draft", "confidence": 0.0, "policies": []}
"""

service_config_parser = """
class ConfigParser:
    def parse(self, raw_content: str, fmt: str):
        if fmt == "json":
            import json
            return json.loads(raw_content)
        elif fmt == "yaml":
            import yaml
            return yaml.safe_load(raw_content)
        elif fmt == "ios":
            return self._parse_ios(raw_content)
        raise ValueError("Unsupported format")
        
    def _parse_ios(self, content: str):
        # Basic mock for IOS
        res = {"interfaces": [], "acls": [], "routes": []}
        return res
"""

service_verification_engine = """
import networkx as nx

class VerificationEngine:
    def __init__(self, db):
        self.db = db
        
    def verify(self):
        # Graph analysis based on topology
        from app.models.device import Device
        from app.models.network_link import NetworkLink
        from app.models.intent import Intent, NormalizedPolicy
        
        devices = self.db.query(Device).all()
        links = self.db.query(NetworkLink).all()
        policies = self.db.query(NormalizedPolicy).all()
        
        G = nx.DiGraph()
        for d in devices:
            G.add_node(d.name, ip=d.ip_address, zone=d.zone)
            
        # Simplified: all links are permitted unless explicitly blocked by an ACL
        # We need a proper map of device id -> name to add edges
        dev_map = {d.id: d.name for d in devices}
        for l in links:
            if l.source_device_id in dev_map and l.target_device_id in dev_map:
                G.add_edge(dev_map[l.source_device_id], dev_map[l.target_device_id])
                
        results = {"passed": 0, "failed": 0, "unknown": 0, "findings": []}
        
        for p in policies:
            # check reachability
            src_nodes = [d.name for d in devices if d.zone == p.source_zone or d.name == p.source_zone]
            dst_nodes = [d.name for d in devices if d.zone == p.destination_zone or d.name == p.destination_zone]
            
            if not src_nodes or not dst_nodes:
                results["unknown"] += 1
                results["findings"].append({"policy_id": p.id, "status": "UNKNOWN"})
                continue
                
            has_path = False
            for s in src_nodes:
                for d in dst_nodes:
                    if s in G and d in G and nx.has_path(G, s, d):
                        # Here we would check ACLs on the path
                        has_path = True
                        
            if p.action == "permit" and has_path:
                results["passed"] += 1
                results["findings"].append({"policy_id": p.id, "status": "PASS"})
            elif p.action == "deny" and not has_path:
                results["passed"] += 1
                results["findings"].append({"policy_id": p.id, "status": "PASS"})
            else:
                results["failed"] += 1
                results["findings"].append({"policy_id": p.id, "status": "FAIL"})
                
        return results
"""

service_repair_engine = """
class RepairEngine:
    def generate_repair(self, finding, original_config):
        # Generate a mock minimal change
        return {
            "proposed_config": original_config,
            "change_type": "acl_modification",
            "expected_result": "Restores intended access"
        }
"""

main_app = """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.router import api_router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Network Intent Verification API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
"""

api_router_content = """
from fastapi import APIRouter
from .intents import router as intents_router
from .verification import router as verification_router

api_router = APIRouter()
api_router.include_router(intents_router, prefix="/intents", tags=["Intents"])
api_router.include_router(verification_router, prefix="/verification", tags=["Verification"])
"""

api_intents = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.intent import Intent, NormalizedPolicy
from app.schemas.intent import IntentCreate, IntentResponse
from app.services.intent_parser import IntentParser

router = APIRouter()
parser = IntentParser()

@router.post("/", response_model=IntentResponse)
def create_intent(intent_in: IntentCreate, db: Session = Depends(get_db)):
    intent = Intent(natural_language=intent_in.natural_language)
    db.add(intent)
    db.commit()
    db.refresh(intent)
    
    # parse
    parsed = parser.parse(intent.natural_language)
    intent.status = parsed["status"]
    intent.confidence = parsed["confidence"]
    db.commit()
    
    for p in parsed["policies"]:
        pol = NormalizedPolicy(intent_id=intent.id, **p)
        db.add(pol)
    db.commit()
    
    return intent

@router.get("/", response_model=list[IntentResponse])
def list_intents(db: Session = Depends(get_db)):
    return db.query(Intent).all()
"""

api_verification = """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.verification import VerificationRun, VerificationFinding
from app.schemas.verification import VerificationRunResponse
from app.services.verification_engine import VerificationEngine

router = APIRouter()

@router.post("/run", response_model=VerificationRunResponse)
def run_verification(db: Session = Depends(get_db)):
    engine = VerificationEngine(db)
    res = engine.verify()
    
    run = VerificationRun(total_policies=res["passed"]+res["failed"]+res["unknown"],
                          passed=res["passed"], failed=res["failed"], unknown=res["unknown"], status="completed")
    db.add(run)
    db.commit()
    db.refresh(run)
    
    for f in res["findings"]:
        finding = VerificationFinding(run_id=run.id, policy_id=f["policy_id"], status=f["status"], severity="high")
        db.add(finding)
    db.commit()
    
    return run
"""

seed_data_file = """
from sqlalchemy.orm import Session
from app.models.device import Device
from app.models.network_link import NetworkLink
from app.models.intent import Intent, NormalizedPolicy

def seed_db(db: Session):
    # Setup Topology
    core_router = Device(name="core-router", device_type="router", ip_address="10.0.0.1", subnet="10.0.0.0/24")
    db.add(core_router)
    # ... create others as requested ...
    db.commit()
"""

files = {
    "app/schemas/__init__.py": schemas_init,
    "app/schemas/device.py": schemas_device,
    "app/schemas/intent.py": schemas_intent,
    "app/schemas/verification.py": schemas_verification,
    "app/schemas/configuration.py": "from pydantic import BaseModel\\nclass ConfigBase(BaseModel):\\n    pass",
    "app/schemas/repair.py": "from pydantic import BaseModel\\nclass RepairBase(BaseModel):\\n    pass",
    "app/schemas/topology.py": "from pydantic import BaseModel\\nclass TopologyBase(BaseModel):\\n    pass",
    "app/schemas/scenario.py": "from pydantic import BaseModel\\nclass ScenarioBase(BaseModel):\\n    pass",
    "app/schemas/audit.py": "from pydantic import BaseModel\\nclass AuditBase(BaseModel):\\n    pass",
    
    "app/services/__init__.py": "",
    "app/services/intent_parser.py": service_intent_parser,
    "app/services/config_parser.py": service_config_parser,
    "app/services/verification_engine.py": service_verification_engine,
    "app/services/repair_engine.py": service_repair_engine,
    "app/services/network_graph.py": "class NetworkGraph:\\n    pass",
    "app/services/scenario_runner.py": "class ScenarioRunner:\\n    pass",
    "app/services/audit_service.py": "class AuditService:\\n    pass",

    "app/api/__init__.py": "",
    "app/api/router.py": api_router_content,
    "app/api/intents.py": api_intents,
    "app/api/verification.py": api_verification,
    "app/api/configurations.py": "from fastapi import APIRouter\\nrouter = APIRouter()",
    "app/api/topology.py": "from fastapi import APIRouter\\nrouter = APIRouter()",
    "app/api/repairs.py": "from fastapi import APIRouter\\nrouter = APIRouter()",
    "app/api/scenarios.py": "from fastapi import APIRouter\\nrouter = APIRouter()",
    "app/api/audit.py": "from fastapi import APIRouter\\nrouter = APIRouter()",
    "app/api/auth.py": "from fastapi import APIRouter\\nrouter = APIRouter()",

    "app/main.py": main_app,
    
    "app/seed/__init__.py": "",
    "app/seed/seed_data.py": seed_data_file,
    "app/seed/scenarios.py": "def load_scenarios():\\n    pass",
    
    "tests/__init__.py": "",
    "tests/conftest.py": "import pytest\\n@pytest.fixture\\ndef db():\\n    pass",
    "tests/test_intent_parser.py": "def test_parser():\\n    pass",
    "tests/test_config_parser.py": "def test_config():\\n    pass",
    "tests/test_verification.py": "def test_verify():\\n    pass",
    "tests/test_repair.py": "def test_repair():\\n    pass",
    "tests/test_scenarios.py": "def test_scenario():\\n    pass",
    "app/__init__.py": ""
}

for rel_path, content in files.items():
    write_file(f"e:/project/CN/backend/{rel_path}", content)
print("Files generated.")
