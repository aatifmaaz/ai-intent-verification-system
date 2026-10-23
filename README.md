# AI-Driven Network Intent Verification and Automated Configuration Repair

## 🎯 Project Overview

An intelligent network management platform that allows network administrators to define desired network behavior using **natural language**, automatically translates those requirements into structured network policies, verifies existing network configurations against the intended behavior, identifies configuration errors, and generates safe, explainable repairs.

> **Simulation-Based**: This system works entirely with simulated network devices. No physical routers, switches, or cloud infrastructure required.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          React Frontend                                │
│   Dashboard │ Intents │ Topology │ Verification │ Repairs │ Simulation │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (JSON)
┌───────────────────────────────────┴────────────────────────────────────┐
│                           FastAPI Backend                              │
│  ┌─────────────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   LLM Intent Parser     │  │Config Parser │  │Verification Engine│  │
│  │ (OpenAI + Deterministic)│  │ (JSON/YAML/  │  │(Graph Reachability│  │
│  │  Prompt-Injection Guard │  │  Cisco IOS)  │  │  + Route & ACL)   │  │
│  └─────────────────────────┘  └──────────────┘  └───────────────────┘  │
│  ┌─────────────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │      Repair Engine      │  │ScenarioRunner│  │   Audit Service   │  │
│  │ (Dry-Run Sandbox, Policy│  │ (Scenarios   │  │ (Reversible Ledger│  │
│  │  Regression Check,      │  │   A thru E)  │  │   & Event Log)    │  │
│  │  Approval & Rollback)   │  │              │  │                   │  │
│  └─────────────────────────┘  └──────────────┘  └───────────────────┘  │
│                                    │                                   │
│                            SQLAlchemy ORM                              │
│                                    │                                   │
│                            SQLite Database                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Core Workflow

```
Natural Language Intent (e.g. "Guest must not access HR")
        │
        ▼
  LLM Parser / Deterministic Fallback
  (With prompt-injection defense & Pydantic schema validation)
        │
        ▼
  Structured Policy (source, dest, protocol, port, action, priority)
        │
        ▼
  Verification Engine (Directed Graph + Static Routes + Ordered ACLs)
        │
        ├── PASS → Logged & Recorded
        ├── UNKNOWN → Flag Missing Data (Empty routes, missing devices)
        └── FAIL → Repair Engine
                      │
                      ▼
              Generate Patch Proposal (ACL rule or Static Route)
                      │
                      ▼
              Validate in Isolated Sandbox Topology
                      │
                      ▼
              Regression Check (Verify all existing passing policies)
                      │
                      ▼
              Human Admin Approval Required
                      │
                      ▼
              Apply to Simulated State (Versioned in Ledger)
                      │
                      ▼
              Re-verify (Confirm Violation Resolved)
                      │
                      ▼
              Optional Rollback (Restores Original Config & State)
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Charts & UI Icons | Recharts, Lucide React |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | SQLite, SQLAlchemy ORM (with Foreign Key constraints) |
| Graph Analysis | NetworkX graph modeling (BFS/DFS, Subgraph path filters) |
| AI / LLM | OpenAI Python SDK (Structured JSON Outputs) with Fallback |
| Testing | pytest (52 automated backend tests), Vite build checks |

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm 9+

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations and backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API Swagger Docs: `http://localhost:8000/docs`

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Start development server
npm run dev
```
Frontend interface: `http://localhost:3000` (or `http://localhost:5173`)

---

## 🧪 Testing & Verification

### Run Automated Backend Test Suite
```bash
python -m pytest backend/tests -v
```
*Current test suite: 52 tests, 100% pass rate.*

### Run Monotonic Performance Benchmark & E2E Lifecycle
```bash
# Windows PowerShell:
$env:PYTHONPATH="backend"; python backend/tests/benchmark_and_e2e.py

# Linux/macOS:
PYTHONPATH=backend python backend/tests/benchmark_and_e2e.py
```

---

## 🎬 The Five Demonstration Scenarios

| Scenario | Objective | Initial Verification | Automated Repair Action | Post-Repair Outcome |
|---|---|---|---|---|
| **Scenario A** | Guest Isolation Violation | **FAIL** (Path exists through firewall) | Adds ordered `deny ip` ACL rule to `main-firewall` | **PASS** (Traffic blocked) |
| **Scenario B** | Missing Route | **FAIL** (Empty routing table on router) | Adds missing subnet route `10.0.2.0/24` to router | **PASS** (Path reachable) |
| **Scenario C** | Unauthorized SSH | **FAIL** (SSH open from any subnet) | Restricts port 22 access to `10.1.40.0/24` | **PASS** (Guest SSH blocked, admin open) |
| **Scenario D** | Database Exposure | **FAIL** (DB port 5432 exposed to guest) | Adds DB isolation rule on border firewall | **PASS** (DB isolated from guest) |
| **Scenario E** | Conflicting Intents | **CONFLICT / FAIL** (Contradictory policies) | Flags conflicting policy IDs with explanation | **EXPLAINED** (Requires admin resolution) |

---

## 🛡️ Security & Safe Repair Principles

1. **Deterministic Verification is Authoritative**: Verification never delegates correctness to an LLM. Graph reachability, IP subnet matches, and ordered ACL evaluations are mathematical and deterministic.
2. **LLM Prompt Injection Defense**: The `LLMIntentParser` actively scans for instruction overrides, privilege escalation keywords, and malicious command injections, blocking adversarial inputs before model execution.
3. **Sandbox Dry-Run**: Repair patches are applied to an isolated deep copy of the network model before touching simulated device state.
4. **Zero-Regression Guarantee**: All existing passing policies are automatically re-evaluated in the candidate state. If an existing policy breaks, the repair proposal is rejected.
5. **Reversible Version Ledger**: Every applied repair archives the preceding configuration version. A single-click rollback restores the previous configuration and verifies state restoration.
6. **Audit Logging**: All intent submissions, verifications, repair approvals, applications, and rollbacks are persisted with timestamps and entity metadata.

---

## ⚠️ Scope & Known Limitations

- **Simulated Environment**: Built strictly for network simulation and educational demonstration; does not deploy live packets to physical hardware.
- **Parser Formats**: Supports JSON, YAML, and Cisco IOS numbered access-lists and static routes. Arbitrary proprietary vendor commands (e.g. BGP confederations, MPLS) report unsupported notices.
- **Database**: SQLite default is optimized for single-tenant local demonstrations. For multi-user concurrent production setups, PostgreSQL is recommended.
