"""
Deterministic Seed Data Generator for Network Intent Verification Platform.
Contains realistic network topology (15 devices), interconnected links,
device configurations with ACLs/routes, seed users, and initial intents/policies.
"""

from sqlalchemy.orm import Session
from datetime import datetime
from app.models.user import User
from app.models.device import Device
from app.models.network_link import NetworkLink
from app.models.intent import Intent, NormalizedPolicy
from app.models.configuration import NetworkConfiguration, ConfigurationVersion
from app.models.verification import VerificationRun, VerificationFinding
from app.models.repair import RepairProposal
from app.models.audit import AuditEvent
from app.database import SessionLocal, engine, Base, utc_now


def reset_demo_data(db: Session):
    """Purge existing records and reseed complete demo topology and policies."""
    db.query(VerificationFinding).delete()
    db.query(VerificationRun).delete()
    db.query(RepairProposal).delete()
    db.query(ConfigurationVersion).delete()
    db.query(NetworkConfiguration).delete()
    db.query(NormalizedPolicy).delete()
    db.query(Intent).delete()
    db.query(NetworkLink).delete()
    db.query(Device).delete()
    db.query(AuditEvent).delete()
    db.query(User).delete()
    db.commit()
    seed_db(db)


def seed_db(db: Session):
    # Check if already seeded
    if db.query(Device).first() is not None:
        return

    # 1. Seed Users
    admin = User(username="admin", role="admin")
    operator = User(username="operator", role="operator")
    db.add_all([admin, operator])
    db.commit()

    # 2. Seed Simulated Network Devices
    devices_data = [
        # Core Infrastructure
        {
            "name": "core-router",
            "device_type": "router",
            "ip_address": "10.0.0.1",
            "subnet": "10.0.0.0/24",
            "zone": "core",
            "vlan_id": 1,
            "interfaces": {
                "GigabitEthernet0/0": {"ip": "10.0.0.1/24", "status": "up"},
                "GigabitEthernet0/1": {"ip": "10.0.1.2/24", "status": "up"},
                "GigabitEthernet0/2": {"ip": "10.0.2.2/24", "status": "up"},
                "GigabitEthernet0/3": {"ip": "10.0.3.10/24", "status": "up"},
            },
            "config": {
                "hostname": "core-router",
                "routes": [
                    {"network": "10.1.10.0", "mask": "255.255.255.0", "next_hop": "10.0.3.1"},
                    {"network": "10.1.20.0", "mask": "255.255.255.0", "next_hop": "10.0.3.1"},
                    {"network": "10.1.50.0", "mask": "255.255.255.0", "next_hop": "10.0.3.2"},
                    {"network": "10.1.60.0", "mask": "255.255.255.0", "next_hop": "10.0.3.2"},
                ],
                "acls": [
                    {
                        "name": "vty-access-in",
                        "rules": [
                            # Deliberate vulnerability: SSH permit any
                            {"action": "permit", "protocol": "tcp", "source": "any", "destination": "any", "port": 22},
                            {"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}
                        ]
                    }
                ]
            }
        },
        {
            "name": "edge-router",
            "device_type": "router",
            "ip_address": "10.0.1.1",
            "subnet": "10.0.1.0/24",
            "zone": "edge",
            "vlan_id": 1,
            "interfaces": {
                "GigabitEthernet0/0": {"ip": "10.0.1.1/24", "status": "up"},
                "GigabitEthernet0/1": {"ip": "198.51.100.1/24", "status": "up"},
            },
            "config": {
                "hostname": "edge-router",
                "routes": [{"network": "0.0.0.0", "mask": "0.0.0.0", "next_hop": "198.51.100.254"}],
                "acls": [
                    {"name": "edge-filter", "rules": [{"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}]}
                ]
            }
        },
        {
            "name": "main-firewall",
            "device_type": "firewall",
            "ip_address": "10.0.2.1",
            "subnet": "10.0.2.0/24",
            "zone": "security",
            "vlan_id": 99,
            "interfaces": {
                "eth0": {"ip": "10.0.2.1/24", "status": "up", "zone": "inside"},
                "eth1": {"ip": "10.1.30.1/24", "status": "up", "zone": "guest"},
                "eth2": {"ip": "10.1.70.1/24", "status": "up", "zone": "dmz"},
            },
            "config": {
                "hostname": "main-firewall",
                "acls": [
                    {
                        "name": "fw-zone-rules",
                        "rules": [
                            # Deliberate violation: Guest allowed to communicate with any (missing guest->hr isolation)
                            {"action": "permit", "protocol": "ip", "source": "10.1.30.0/24", "destination": "10.1.10.0/24", "port": "any"},
                            # Deliberate violation: Database port 3306 reachable from guest
                            {"action": "permit", "protocol": "tcp", "source": "10.1.30.0/24", "destination": "10.1.60.0/24", "port": 3306},
                            # General permit
                            {"action": "permit", "protocol": "ip", "source": "10.1.20.0/24", "destination": "10.1.50.0/24", "port": "any"},
                            {"action": "permit", "protocol": "ip", "source": "10.1.40.0/24", "destination": "any", "port": "any"},
                            {"action": "permit", "protocol": "ip", "source": "any", "destination": "any", "port": "any"}
                        ]
                    }
                ]
            }
        },
        {
            "name": "distribution-switch-1",
            "device_type": "switch",
            "ip_address": "10.0.3.1",
            "subnet": "10.0.3.0/24",
            "zone": "distribution",
            "vlan_id": 1,
            "interfaces": {"vlan1": {"ip": "10.0.3.1/24", "status": "up"}},
            "config": {"hostname": "distribution-switch-1", "vlans": [{"id": 100, "name": "HR"}, {"id": 200, "name": "Engineering"}, {"id": 400, "name": "Management"}]}
        },
        {
            "name": "distribution-switch-2",
            "device_type": "switch",
            "ip_address": "10.0.3.2",
            "subnet": "10.0.3.0/24",
            "zone": "distribution",
            "vlan_id": 1,
            "interfaces": {"vlan1": {"ip": "10.0.3.2/24", "status": "up"}},
            "config": {"hostname": "distribution-switch-2", "vlans": [{"id": 300, "name": "Guest"}, {"id": 500, "name": "Application"}, {"id": 600, "name": "Database"}]}
        },
        # Servers
        {
            "name": "hr-server",
            "device_type": "server",
            "ip_address": "10.1.10.5",
            "subnet": "10.1.10.0/24",
            "zone": "hr",
            "vlan_id": 100,
            "interfaces": {"eth0": {"ip": "10.1.10.5/24", "status": "up"}},
            "config": {"hostname": "hr-server", "services": ["https", "hr-portal"]}
        },
        {
            "name": "eng-server",
            "device_type": "server",
            "ip_address": "10.1.20.5",
            "subnet": "10.1.20.0/24",
            "zone": "engineering",
            "vlan_id": 200,
            "interfaces": {"eth0": {"ip": "10.1.20.5/24", "status": "up"}},
            "config": {"hostname": "eng-server", "services": ["git", "build-runner"]}
        },
        {
            "name": "app-server",
            "device_type": "server",
            "ip_address": "10.1.50.10",
            "subnet": "10.1.50.0/24",
            "zone": "application",
            "vlan_id": 500,
            "interfaces": {"eth0": {"ip": "10.1.50.10/24", "status": "up"}},
            "config": {"hostname": "app-server", "services": ["http", "https", "api"]}
        },
        {
            "name": "db-server",
            "device_type": "server",
            "ip_address": "10.1.60.15",
            "subnet": "10.1.60.0/24",
            "zone": "database",
            "vlan_id": 600,
            "interfaces": {"eth0": {"ip": "10.1.60.15/24", "status": "up"}},
            "config": {"hostname": "db-server", "services": ["mysql-3306"]}
        },
        {
            "name": "web-server",
            "device_type": "server",
            "ip_address": "10.1.70.10",
            "subnet": "10.1.70.0/24",
            "zone": "dmz",
            "vlan_id": 700,
            "interfaces": {"eth0": {"ip": "10.1.70.10/24", "status": "up"}},
            "config": {"hostname": "web-server", "services": ["http-80", "https-443"]}
        },
        {
            "name": "backup-server",
            "device_type": "server",
            "ip_address": "10.1.80.20",
            "subnet": "10.1.80.0/24",
            "zone": "backup",
            "vlan_id": 800,
            "interfaces": {"eth0": {"ip": "10.1.80.20/24", "status": "up"}},
            "config": {"hostname": "backup-server", "services": ["storage-agent"]}
        },
        # Client Networks
        {
            "name": "hr-clients",
            "device_type": "client",
            "ip_address": "10.1.10.100",
            "subnet": "10.1.10.0/24",
            "zone": "hr",
            "vlan_id": 100,
            "interfaces": {"eth0": {"ip": "10.1.10.100/24", "status": "up"}},
            "config": {"hostname": "hr-clients-pool"}
        },
        {
            "name": "eng-clients",
            "device_type": "client",
            "ip_address": "10.1.20.100",
            "subnet": "10.1.20.0/24",
            "zone": "engineering",
            "vlan_id": 200,
            "interfaces": {"eth0": {"ip": "10.1.20.100/24", "status": "up"}},
            "config": {"hostname": "eng-workstations"}
        },
        {
            "name": "guest-clients",
            "device_type": "client",
            "ip_address": "10.1.30.100",
            "subnet": "10.1.30.0/24",
            "zone": "guest",
            "vlan_id": 300,
            "interfaces": {"wlan0": {"ip": "10.1.30.100/24", "status": "up"}},
            "config": {"hostname": "guest-wifi-pool"}
        },
        {
            "name": "mgmt-clients",
            "device_type": "client",
            "ip_address": "10.1.40.100",
            "subnet": "10.1.40.0/24",
            "zone": "management",
            "vlan_id": 400,
            "interfaces": {"eth0": {"ip": "10.1.40.100/24", "status": "up"}},
            "config": {"hostname": "noc-admin-workstations"}
        },
    ]

    dev_objs = {}
    for data in devices_data:
        d = Device(**data)
        db.add(d)
        db.flush()
        dev_objs[d.name] = d

    # 3. Seed Network Links
    links_data = [
        # Backbone Interconnects
        ("edge-router", "core-router", "GigabitEthernet0/0", "GigabitEthernet0/1"),
        ("core-router", "main-firewall", "GigabitEthernet0/2", "eth0"),
        ("core-router", "distribution-switch-1", "GigabitEthernet0/0", "vlan1"),
        ("core-router", "distribution-switch-2", "GigabitEthernet0/3", "vlan1"),
        ("distribution-switch-1", "distribution-switch-2", "Trunk1", "Trunk1"),

        # Switch 1 Connections (HR, Eng, Mgmt)
        ("distribution-switch-1", "hr-server", "FastEthernet0/1", "eth0"),
        ("distribution-switch-1", "hr-clients", "FastEthernet0/2", "eth0"),
        ("distribution-switch-1", "eng-server", "FastEthernet0/3", "eth0"),
        ("distribution-switch-1", "eng-clients", "FastEthernet0/4", "eth0"),
        ("distribution-switch-1", "mgmt-clients", "FastEthernet0/5", "eth0"),

        # Switch 2 Connections (App, DB, Backup)
        ("distribution-switch-2", "app-server", "FastEthernet0/1", "eth0"),
        ("distribution-switch-2", "db-server", "FastEthernet0/2", "eth0"),
        ("distribution-switch-2", "backup-server", "FastEthernet0/3", "eth0"),

        # Firewall Connections (Guest, DMZ/Web)
        ("main-firewall", "guest-clients", "eth1", "wlan0"),
        ("main-firewall", "web-server", "eth2", "eth0"),
    ]

    for src_name, tgt_name, src_if, tgt_if in links_data:
        link = NetworkLink(
            source_device_id=dev_objs[src_name].id,
            target_device_id=dev_objs[tgt_name].id,
            source_interface=src_if,
            target_interface=tgt_if,
            link_type="ethernet",
            bandwidth="1Gbps",
            status="up"
        )
        db.add(link)

    # 4. Seed Standard Sample Intents and Normalized Policies
    intents_seed = [
        {
            "nl": "The HR network must not communicate with the guest network.",
            "status": "parsed",
            "confidence": 0.95,
            "assumptions": {"detected_intent": "isolation", "source": "hr", "target": "guest"},
            "policies": [
                {
                    "policy_type": "deny",
                    "source_zone": "guest",
                    "destination_zone": "hr",
                    "protocol": "any",
                    "port": "any",
                    "action": "deny",
                    "priority": 10
                }
            ]
        },
        {
            "nl": "All devices in the engineering network must be able to access the internal application server.",
            "status": "parsed",
            "confidence": 0.92,
            "assumptions": {"detected_intent": "connectivity", "source": "engineering", "target": "application"},
            "policies": [
                {
                    "policy_type": "allow",
                    "source_zone": "engineering",
                    "destination_zone": "application",
                    "protocol": "any",
                    "port": "any",
                    "action": "permit",
                    "priority": 20
                }
            ]
        },
        {
            "nl": "Only administrators may access network devices using SSH.",
            "status": "parsed",
            "confidence": 0.90,
            "assumptions": {"detected_intent": "restriction", "source": "management", "target": "core"},
            "policies": [
                {
                    "policy_type": "restrict",
                    "source_zone": "management",
                    "destination_zone": "core",
                    "protocol": "tcp",
                    "port": "22",
                    "action": "permit",
                    "priority": 30
                }
            ]
        },
        {
            "nl": "Database access must remain restricted to the application server.",
            "status": "parsed",
            "confidence": 0.93,
            "assumptions": {"detected_intent": "database_isolation", "source": "application", "target": "database"},
            "policies": [
                {
                    "policy_type": "deny",
                    "source_zone": "guest",
                    "destination_zone": "database",
                    "protocol": "tcp",
                    "port": "3306",
                    "action": "deny",
                    "priority": 40
                }
            ]
        },
        {
            "nl": "The backup network must remain isolated from ordinary user traffic.",
            "status": "parsed",
            "confidence": 0.94,
            "assumptions": {"detected_intent": "backup_isolation", "source": "hr", "target": "backup"},
            "policies": [
                {
                    "policy_type": "isolate",
                    "source_zone": "hr",
                    "destination_zone": "backup",
                    "protocol": "any",
                    "port": "any",
                    "action": "deny",
                    "priority": 50
                }
            ]
        }
    ]

    for item in intents_seed:
        intent = Intent(
            natural_language=item["nl"],
            status=item["status"],
            confidence=item["confidence"],
            assumptions=item["assumptions"],
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(intent)
        db.flush()

        for p in item["policies"]:
            pol = NormalizedPolicy(
                intent_id=intent.id,
                policy_type=p["policy_type"],
                source_zone=p.get("source_zone"),
                source_network=p.get("source_network"),
                destination_zone=p.get("destination_zone"),
                destination_network=p.get("destination_network"),
                protocol=p.get("protocol"),
                port=p.get("port"),
                action=p["action"],
                priority=p["priority"]
            )
            db.add(pol)

    # 5. Seed Initial Audit Log
    db.add(AuditEvent(
        event_type="system_bootstrap",
        description="Demo network topology (15 devices, 6 zones) initialized with seed intents.",
        user_id=admin.id,
        details={"devices_count": len(devices_data), "links_count": len(links_data), "intents_count": len(intents_seed)}
    ))

    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        reset_demo_data(db)
        print("Demo database successfully seeded!")
    finally:
        db.close()
