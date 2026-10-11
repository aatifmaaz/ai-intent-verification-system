# AI-Driven Network Intent Verification and Automated Configuration Repair

## 🎯 Project Overview

An intelligent network management platform that allows network administrators to define desired network behavior using **natural language**, automatically translates those requirements into structured network policies, verifies existing network configurations against the intended behavior, identifies configuration errors, and generates safe, explainable repairs.

> **Simulation-Based**: This system works entirely with simulated network devices. No physical routers, switches, or cloud infrastructure required.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  Dashboard │ Intents │ Topology │ Verification │ Repair  │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API (JSON)
┌─────────────────────┴───────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │  Intent   │ │  Config  │ │Verification│ │  Repair  │ │
│  │  Parser   │ │  Parser  │ │  Engine    │ │  Engine  │ │
│  └──────────┘ └──────────┘ └────────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐              │
│  │ Network  │ │ Scenario │ │   Audit    │              │
│  │  Graph   │ │  Runner  │ │  Service   │              │
│  └──────────┘ └──────────┘ └────────────┘              │
│                      │                                   │
│              SQLAlchemy ORM                              │
│                      │                                   │
│              SQLite Database                             │
└─────────────────────────────────────────────────────────┘
```

## 🔄 Core Workflow

```
Natural Language Intent
        │
        ▼
  Intent Parser (Deterministic NLP)
        │
        ▼
  Structured Policy (source, dest, protocol, port, action)
        │
        ▼
  Verification Engine (Graph + Rules)
        │
        ├── PASS → Log & Report
        ├── UNKNOWN → Flag Missing Data
        └── FAIL → Repair Engine
                      │
                      ▼
              Generate Minimal Repair
                      │
                      ▼
              Validate in Isolation
                      │
                      ▼
              Admin Approval Required
                      │
                      ▼
              Apply & Re-verify
```

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | SQLite (dev), SQLAlchemy ORM |
| Graph Analysis | NetworkX-style graph algorithms |
| Testing | pytest (backend), Vitest (frontend) |
| Deployment | Docker, Docker Compose |

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Initialize database with seed data
python -m app.seed.seed_data

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env

# Development
npm run dev

# Production build
npm run build
```

### Docker
```bash
docker-compose up --build
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/intents | Create and normalize an intent |
| GET | /api/intents | List stored intents |
| POST | /api/configurations/import | Import and parse a configuration |
| GET | /api/topology | Retrieve current topology |
| POST | /api/verification/run | Execute verification engine |
| GET | /api/verification/results | Retrieve verification results |
| POST | /api/repairs/propose | Generate repair proposal |
| POST | /api/repairs/validate | Validate proposed patch |
| POST | /api/repairs/{id}/approve | Approve and apply repair |
| POST | /api/repairs/{id}/rollback | Roll back applied repair |
| GET | /api/audit-logs | Retrieve audit history |
| GET | /api/scenarios | List demo scenarios |
| POST | /api/scenarios/{id}/run | Execute a scenario |

Full API documentation available at: `http://localhost:8000/docs`

## 🧪 Demo Scenarios

| ID | Scenario | Description |
|----|----------|-------------|
| A | Guest Isolation Violation | Guest VLAN can access HR server |
| B | Missing Route | Engineering can't reach app server |
| C | Unauthorized SSH Access | Device allows SSH from unauthorized subnet |
| D | Database Exposure | DB server reachable from guest network |
| E | Conflicting Intents | Contradictory connectivity policies |

## 🔍 Verification Algorithm

The verification engine uses **deterministic rule-based analysis** combined with **graph-based reachability checks**:

1. **Graph Construction**: Network topology is modeled as a directed graph where devices are nodes and links are edges
2. **ACL Overlay**: Access control lists are applied as edge filters — a physical link does not imply logical reachability
3. **Policy Evaluation**: Each policy is checked against the graph:
   - **DENY/ISOLATE**: BFS/DFS checks that no permitted path exists between source and destination zones
   - **ALLOW/REQUIRE**: BFS/DFS verifies at least one permitted path exists
   - **RESTRICT**: Verifies only authorized source networks can reach the destination
4. **Evidence Collection**: Every check records the specific configuration facts that support the conclusion

### Why Deterministic Verification?

An LLM cannot reliably determine network correctness because:
- Network policies require **exact** matching of IP ranges, port numbers, and protocol rules
- Graph reachability is a **mathematical property** that must be computed, not guessed
- Safety-critical decisions (blocking traffic, opening ports) must be **reproducible and auditable**
- Deterministic verification provides **consistent results** across runs

## 🔧 Repair Algorithm

1. **Root Cause Analysis**: Identify which specific configuration element causes the violation
2. **Minimal Change Generation**: Produce the smallest config change that resolves the issue
3. **Safety Validation**: Check that the repair doesn't lock out admins, expose restricted services, or create new violations
4. **Isolated Testing**: Apply repair to a copy of the config and re-run all policies
5. **Regression Check**: Verify no previously-passing policies now fail
6. **Human Approval**: Administrator must explicitly approve before changes are committed

## 📁 Project Structure

```
CN/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   └── seed/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## ⚠️ Known Limitations

- **Simulation only**: No real network device integration
- **Vendor support**: Currently supports JSON/YAML and basic Cisco IOS format
- **Scale**: SQLite suitable for development; migrate to PostgreSQL for production
- **AI provider**: LLM integration is optional; deterministic parser handles core intents

## 🚀 Future Enhancements

- PostgreSQL migration for production deployment
- Real device integration via NETCONF/RESTCONF
- Multi-vendor config support (Juniper, Arista, Palo Alto)
- Role-based access control with JWT authentication
- WebSocket-based real-time notifications
- Configuration drift monitoring
- Scheduled verification runs
- SNMP/streaming telemetry integration

## 📄 License

MIT License - See LICENSE file for details.
