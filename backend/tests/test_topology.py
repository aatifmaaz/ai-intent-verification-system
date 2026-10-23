import pytest
from app.models.device import Device
from app.models.network_link import NetworkLink
from app.models.intent import Intent
from app.services.verification_engine import VerificationEngine


def test_get_topology_templates(client):
    response = client.get("/api/topology/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 4
    template_ids = [t["id"] for t in templates]
    assert "enterprise" in template_ids
    assert "datacenter" in template_ids
    assert "healthcare" in template_ids
    assert "fintech" in template_ids


def test_load_topology_template(client, db_session):
    # Load Datacenter template
    response = client.post("/api/topology/templates/datacenter/load")
    assert response.status_code == 200
    data = response.json()
    assert "Cloud Spine-Leaf" in data["template_name"]
    assert data["devices_count"] == 13
    assert data["links_count"] == 15
    
    # Verify in DB
    devices = db_session.query(Device).all()
    assert len(devices) == 13
    names = [d.name for d in devices]
    assert "spine-switch-01" in names
    assert "leaf-switch-01" in names
    assert "k8s-control-plane" in names
    
    # Run verification engine on the new datacenter topology
    engine = VerificationEngine(db_session)
    run = engine.verify()
    assert run.status == "completed"


def test_import_custom_new_topology(client, db_session):
    custom_topology_payload = {
        "name": "Smart Campus IoT Mesh",
        "devices": [
            {"name": "gateway-router", "device_type": "router", "ip_address": "172.16.0.1", "subnet": "172.16.0.0/24", "zone": "edge"},
            {"name": "core-firewall", "device_type": "firewall", "ip_address": "172.16.0.2", "subnet": "172.16.0.0/24", "zone": "perimeter"},
            {"name": "iot-sensor-hub", "device_type": "client", "ip_address": "172.16.10.10", "subnet": "172.16.10.0/24", "zone": "iot"},
            {"name": "analytics-server", "device_type": "server", "ip_address": "172.16.20.50", "subnet": "172.16.20.0/24", "zone": "analytics"},
            {"name": "campus-guest-ap", "device_type": "client", "ip_address": "172.16.30.100", "subnet": "172.16.30.0/24", "zone": "guest"}
        ],
        "links": [
            {"source": "gateway-router", "target": "core-firewall"},
            {"source": "core-firewall", "target": "iot-sensor-hub"},
            {"source": "core-firewall", "target": "analytics-server"},
            {"source": "core-firewall", "target": "campus-guest-ap"}
        ],
        "intents": [
            "Campus guest AP must not communicate with the IoT sensor hub.",
            "Analytics server must remain isolated from campus guest AP."
        ]
    }
    
    response = client.post("/api/topology/import", json=custom_topology_payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["devices_count"] == 5
    assert res["links_count"] == 4
    assert res["intents_count"] == 2
    
    # Verify in DB
    devices = db_session.query(Device).all()
    assert len(devices) == 5
    device_names = {d.name for d in devices}
    assert "iot-sensor-hub" in device_names
    assert "analytics-server" in device_names
    
    links = db_session.query(NetworkLink).all()
    assert len(links) == 4
    
    intents = db_session.query(Intent).all()
    assert len(intents) == 2
    
    # Test Auto-Pilot intent enforcement against this custom topology
    auto_response = client.post("/api/intents/auto-enforce", json={
        "natural_language": "Isolate the IoT sensor hub completely from analytics server"
    })
    auto_data = auto_response.json()
    assert auto_data["status"] in ["COMPLIANT", "REMEDIATED", "UNKNOWN", "FAIL"]
    assert "intent" in auto_data
    assert auto_data["intent"]["natural_language"] == "Isolate the IoT sensor hub completely from analytics server"


def test_add_dynamic_device(client, db_session):
    device_payload = {
        "name": "edge-accelerator-01",
        "device_type": "server",
        "ip_address": "10.1.99.10",
        "subnet": "10.1.99.0/24",
        "zone": "accelerator"
    }
    response = client.post("/api/topology/device", json=device_payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "edge-accelerator-01"
    assert created["zone"] == "accelerator"
    
    # Check in DB
    dev = db_session.query(Device).filter(Device.name == "edge-accelerator-01").first()
    assert dev is not None
