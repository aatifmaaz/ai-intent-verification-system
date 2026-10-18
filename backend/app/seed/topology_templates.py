"""
Network Topology Templates for On-Demand Network Switching and Testing.
Provides realistic network topologies across multiple enterprise domains:
1. Enterprise Campus (Default)
2. Cloud Spine-Leaf Datacenter
3. Smart Healthcare Zero-Trust Hospital
4. FinTech Banking Payment Perimeter
"""

from typing import Dict, Any, List

TOPOLOGY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise Campus Network",
        "description": "Multi-tier corporate campus with edge routing, distribution switches, department zones, and demilitarized perimeter.",
        "devices": [
            {"name": "core-router", "device_type": "router", "ip_address": "10.0.0.1", "subnet": "10.0.0.0/24", "zone": "core", "vlan_id": 1},
            {"name": "edge-router", "device_type": "router", "ip_address": "10.0.1.1", "subnet": "10.0.1.0/24", "zone": "edge", "vlan_id": 2},
            {
                "name": "main-firewall", "device_type": "firewall", "ip_address": "10.0.2.1", "subnet": "10.0.2.0/24", "zone": "security", "vlan_id": 99,
                "config": {
                    "acls": [
                        {
                            "name": "PERIMETER-FILTER",
                            "rules": [
                                {"action": "deny", "protocol": "ip", "source": "10.1.30.0/24", "destination": "10.1.60.0/24", "port": "any"},
                                {"action": "permit", "protocol": "tcp", "source": "any", "destination": "10.1.70.10", "port": "443"}
                            ]
                        }
                    ]
                }
            },
            {"name": "distribution-switch-1", "device_type": "switch", "ip_address": "10.0.3.1", "subnet": "10.0.3.0/24", "zone": "distribution", "vlan_id": 10},
            {"name": "distribution-switch-2", "device_type": "switch", "ip_address": "10.0.3.2", "subnet": "10.0.3.0/24", "zone": "distribution", "vlan_id": 10},
            {"name": "hr-server", "device_type": "server", "ip_address": "10.1.10.5", "subnet": "10.1.10.0/24", "zone": "hr", "vlan_id": 100},
            {"name": "eng-server", "device_type": "server", "ip_address": "10.1.20.5", "subnet": "10.1.20.0/24", "zone": "engineering", "vlan_id": 200},
            {"name": "app-server", "device_type": "server", "ip_address": "10.1.50.10", "subnet": "10.1.50.0/24", "zone": "application", "vlan_id": 500},
            {"name": "db-server", "device_type": "server", "ip_address": "10.1.60.15", "subnet": "10.1.60.0/24", "zone": "database", "vlan_id": 600},
            {"name": "web-server", "device_type": "server", "ip_address": "10.1.70.10", "subnet": "10.1.70.0/24", "zone": "dmz", "vlan_id": 700},
            {"name": "backup-server", "device_type": "server", "ip_address": "10.1.80.20", "subnet": "10.1.80.0/24", "zone": "backup", "vlan_id": 800},
            {"name": "hr-clients", "device_type": "client", "ip_address": "10.1.10.100", "subnet": "10.1.10.0/24", "zone": "hr", "vlan_id": 100},
            {"name": "eng-clients", "device_type": "client", "ip_address": "10.1.20.100", "subnet": "10.1.20.0/24", "zone": "engineering", "vlan_id": 200},
            {"name": "guest-clients", "device_type": "client", "ip_address": "10.1.30.100", "subnet": "10.1.30.0/24", "zone": "guest", "vlan_id": 300},
            {"name": "mgmt-clients", "device_type": "client", "ip_address": "10.1.40.100", "subnet": "10.1.40.0/24", "zone": "management", "vlan_id": 400}
        ],
        "links": [
            ("edge-router", "core-router"),
            ("core-router", "main-firewall"),
            ("core-router", "distribution-switch-1"),
            ("core-router", "distribution-switch-2"),
            ("distribution-switch-1", "distribution-switch-2"),
            ("distribution-switch-1", "hr-server"),
            ("distribution-switch-1", "hr-clients"),
            ("distribution-switch-1", "eng-server"),
            ("distribution-switch-1", "eng-clients"),
            ("distribution-switch-1", "mgmt-clients"),
            ("distribution-switch-2", "app-server"),
            ("distribution-switch-2", "db-server"),
            ("distribution-switch-2", "backup-server"),
            ("main-firewall", "guest-clients"),
            ("main-firewall", "web-server")
        ],
        "sample_intents": [
            "The guest network must not communicate with the HR network.",
            "All devices in the engineering network must be able to access the internal application server."
        ]
    },

    "datacenter": {
        "id": "datacenter",
        "name": "Cloud Spine-Leaf Data Center",
        "description": "High-bandwidth BGP Clos fabric interconnecting Kubernetes compute clusters, managed databases, and caching tiers.",
        "devices": [
            {"name": "spine-switch-01", "device_type": "router", "ip_address": "172.16.0.1", "subnet": "172.16.0.0/24", "zone": "spine", "vlan_id": 10},
            {"name": "spine-switch-02", "device_type": "router", "ip_address": "172.16.0.2", "subnet": "172.16.0.0/24", "zone": "spine", "vlan_id": 10},
            {"name": "leaf-switch-01", "device_type": "switch", "ip_address": "172.16.1.1", "subnet": "172.16.1.0/24", "zone": "leaf", "vlan_id": 20},
            {"name": "leaf-switch-02", "device_type": "switch", "ip_address": "172.16.2.1", "subnet": "172.16.2.0/24", "zone": "leaf", "vlan_id": 20},
            {"name": "leaf-switch-03", "device_type": "switch", "ip_address": "172.16.3.1", "subnet": "172.16.3.0/24", "zone": "leaf", "vlan_id": 20},
            {"name": "border-firewall", "device_type": "firewall", "ip_address": "172.16.99.1", "subnet": "172.16.99.0/24", "zone": "perimeter", "vlan_id": 99},
            {"name": "ingress-proxy", "device_type": "server", "ip_address": "172.20.10.5", "subnet": "172.20.10.0/24", "zone": "dmz", "vlan_id": 100},
            {"name": "k8s-control-plane", "device_type": "server", "ip_address": "172.20.20.10", "subnet": "172.20.20.0/24", "zone": "compute", "vlan_id": 200},
            {"name": "k8s-worker-node-1", "device_type": "server", "ip_address": "172.20.20.11", "subnet": "172.20.20.0/24", "zone": "compute", "vlan_id": 200},
            {"name": "k8s-worker-node-2", "device_type": "server", "ip_address": "172.20.20.12", "subnet": "172.20.20.0/24", "zone": "compute", "vlan_id": 200},
            {"name": "postgres-cluster", "device_type": "server", "ip_address": "172.20.30.50", "subnet": "172.20.30.0/24", "zone": "database", "vlan_id": 300},
            {"name": "redis-cache", "device_type": "server", "ip_address": "172.20.30.60", "subnet": "172.20.30.0/24", "zone": "database", "vlan_id": 300},
            {"name": "bastion-host", "device_type": "client", "ip_address": "172.20.40.100", "subnet": "172.20.40.0/24", "zone": "management", "vlan_id": 400}
        ],
        "links": [
            ("border-firewall", "spine-switch-01"),
            ("border-firewall", "spine-switch-02"),
            ("spine-switch-01", "leaf-switch-01"),
            ("spine-switch-01", "leaf-switch-02"),
            ("spine-switch-01", "leaf-switch-03"),
            ("spine-switch-02", "leaf-switch-01"),
            ("spine-switch-02", "leaf-switch-02"),
            ("spine-switch-02", "leaf-switch-03"),
            ("leaf-switch-01", "ingress-proxy"),
            ("leaf-switch-01", "bastion-host"),
            ("leaf-switch-02", "k8s-control-plane"),
            ("leaf-switch-02", "k8s-worker-node-1"),
            ("leaf-switch-02", "k8s-worker-node-2"),
            ("leaf-switch-03", "postgres-cluster"),
            ("leaf-switch-03", "redis-cache")
        ],
        "sample_intents": [
            "External traffic must not directly access the postgres cluster.",
            "Only the bastion host may access the k8s control plane using SSH."
        ]
    },

    "healthcare": {
        "id": "healthcare",
        "name": "Smart Hospital Zero-Trust Mesh",
        "description": "Critical care hospital network isolating IoT medical devices (MRI/infusion pumps) from electronic health records (EHR) and public patient Wi-Fi.",
        "devices": [
            {"name": "med-core-gateway", "device_type": "router", "ip_address": "192.168.0.1", "subnet": "192.168.0.0/24", "zone": "core", "vlan_id": 1},
            {"name": "biomed-firewall", "device_type": "firewall", "ip_address": "192.168.1.1", "subnet": "192.168.1.0/24", "zone": "security", "vlan_id": 50},
            {"name": "clinical-switch", "device_type": "switch", "ip_address": "192.168.2.1", "subnet": "192.168.2.0/24", "zone": "clinical", "vlan_id": 10},
            {"name": "iot-med-switch", "device_type": "switch", "ip_address": "192.168.3.1", "subnet": "192.168.3.0/24", "zone": "biomed", "vlan_id": 20},
            {"name": "ehr-database", "device_type": "server", "ip_address": "192.168.10.5", "subnet": "192.168.10.0/24", "zone": "database", "vlan_id": 100},
            {"name": "pacs-imaging-server", "device_type": "server", "ip_address": "192.168.10.15", "subnet": "192.168.10.0/24", "zone": "database", "vlan_id": 100},
            {"name": "mri-scanner", "device_type": "server", "ip_address": "192.168.20.30", "subnet": "192.168.20.0/24", "zone": "iot-devices", "vlan_id": 200},
            {"name": "infusion-pumps", "device_type": "client", "ip_address": "192.168.20.40", "subnet": "192.168.20.0/24", "zone": "iot-devices", "vlan_id": 200},
            {"name": "doctors-workstations", "device_type": "client", "ip_address": "192.168.30.100", "subnet": "192.168.30.0/24", "zone": "clinical", "vlan_id": 300},
            {"name": "icu-nurses-station", "device_type": "client", "ip_address": "192.168.30.105", "subnet": "192.168.30.0/24", "zone": "clinical", "vlan_id": 300},
            {"name": "visitor-patient-wifi", "device_type": "client", "ip_address": "192.168.40.100", "subnet": "192.168.40.0/24", "zone": "guest", "vlan_id": 400}
        ],
        "links": [
            ("med-core-gateway", "biomed-firewall"),
            ("med-core-gateway", "clinical-switch"),
            ("biomed-firewall", "iot-med-switch"),
            ("biomed-firewall", "visitor-patient-wifi"),
            ("clinical-switch", "ehr-database"),
            ("clinical-switch", "pacs-imaging-server"),
            ("clinical-switch", "doctors-workstations"),
            ("clinical-switch", "icu-nurses-station"),
            ("iot-med-switch", "mri-scanner"),
            ("iot-med-switch", "infusion-pumps")
        ],
        "sample_intents": [
            "Visitor patient wifi must not communicate with the EHR database.",
            "Medical IoT devices must remain isolated from visitor wifi."
        ]
    },

    "fintech": {
        "id": "fintech",
        "name": "FinTech Banking Payment Perimeter",
        "description": "High-assurance PCI-DSS banking network isolating cardholder data environments, transaction switches, and administrative jump boxes.",
        "devices": [
            {"name": "border-pci-gateway", "device_type": "router", "ip_address": "10.200.0.1", "subnet": "10.200.0.0/24", "zone": "edge", "vlan_id": 1},
            {"name": "pci-dss-firewall", "device_type": "firewall", "ip_address": "10.200.1.1", "subnet": "10.200.1.0/24", "zone": "security", "vlan_id": 99},
            {"name": "core-banking-switch", "device_type": "switch", "ip_address": "10.200.2.1", "subnet": "10.200.2.0/24", "zone": "core", "vlan_id": 10},
            {"name": "payment-api-gateway", "device_type": "server", "ip_address": "10.200.10.5", "subnet": "10.200.10.0/24", "zone": "dmz", "vlan_id": 100},
            {"name": "atm-transaction-switch", "device_type": "server", "ip_address": "10.200.10.20", "subnet": "10.200.10.0/24", "zone": "core", "vlan_id": 150},
            {"name": "cardholder-vault-db", "device_type": "server", "ip_address": "10.200.20.10", "subnet": "10.200.20.0/24", "zone": "database", "vlan_id": 200},
            {"name": "fraud-analytics-engine", "device_type": "server", "ip_address": "10.200.20.25", "subnet": "10.200.20.0/24", "zone": "application", "vlan_id": 250},
            {"name": "swift-transfer-node", "device_type": "server", "ip_address": "10.200.30.5", "subnet": "10.200.30.0/24", "zone": "banking", "vlan_id": 300},
            {"name": "compliance-audit-logger", "device_type": "server", "ip_address": "10.200.30.50", "subnet": "10.200.30.0/24", "zone": "backup", "vlan_id": 350},
            {"name": "teller-workstations", "device_type": "client", "ip_address": "10.200.40.100", "subnet": "10.200.40.0/24", "zone": "internal", "vlan_id": 400},
            {"name": "admin-jump-host", "device_type": "client", "ip_address": "10.200.50.10", "subnet": "10.200.50.0/24", "zone": "management", "vlan_id": 500}
        ],
        "links": [
            ("border-pci-gateway", "pci-dss-firewall"),
            ("pci-dss-firewall", "payment-api-gateway"),
            ("pci-dss-firewall", "core-banking-switch"),
            ("core-banking-switch", "atm-transaction-switch"),
            ("core-banking-switch", "cardholder-vault-db"),
            ("core-banking-switch", "fraud-analytics-engine"),
            ("core-banking-switch", "swift-transfer-node"),
            ("core-banking-switch", "compliance-audit-logger"),
            ("core-banking-switch", "teller-workstations"),
            ("core-banking-switch", "admin-jump-host")
        ],
        "sample_intents": [
            "Payment API gateway must not communicate directly with the cardholder vault database.",
            "Only admin jump host may access core banking switch using SSH."
        ]
    }
}
