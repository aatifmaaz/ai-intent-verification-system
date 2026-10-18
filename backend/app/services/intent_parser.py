import re
import ipaddress
from typing import Optional, Dict, Any, List

class IntentParser:
    def __init__(self):
        # Comprehensive multi-topology lexical ontology covering Enterprise, Cloud Datacenter,
        # Smart Healthcare, FinTech Banking, Retail Branch, and General Zero-Trust
        self.zone_synonyms = {
            "guest": [
                "guest", "guests", "guest network", "guest wifi", "guest-wifi", "guest-clients", 
                "guest vlan", "visitor", "visitors", "visitor-patient-wifi", "visitor wifi", 
                "patient wifi", "patient-wifi", "customer-guest-wifi", "customer wifi", 
                "byod", "contractor", "contractors", "untrusted", "public wifi", 
                "client", "clients", "laptop", "laptops", "mobile", "bad guys", "hackers", 
                "outsiders", "unauthorized users", "external users", "attackers"
            ],
            "hr": [
                "hr", "human resources", "human-resources", "hr network", "hr department", 
                "hr-server", "hr-clients", "payroll", "personnel", "staff", "employee", "employees", "office"
            ],
            "engineering": [
                "engineering", "eng", "developers", "dev", "devs", "developer", "eng-server", 
                "eng-clients", "code", "git", "ci-cd", "rnd", "research", "tech"
            ],
            "database": [
                "database", "databases", "db", "dbs", "db-server", "sql", "mysql", "postgres", 
                "postgres-cluster", "postgresql", "oracle", "mongo", "ehr-database", "ehr", 
                "cardholder-vault-db", "cardholder vault", "vault", "inventory-db", "inventory database", 
                "storage", "records", "data store", "sensitive files", "customer records", "financial records"
            ],
            "dmz": [
                "dmz", "web", "web server", "web-server", "website", "demilitarized zone", 
                "external facing", "public facing", "proxy", "frontend", "nginx", 
                "payment-api-gateway", "payment api", "ingress-proxy", "ingress"
            ],
            "management": [
                "management", "mgmt", "admin", "admins", "administrator", "administrators", 
                "mgmt-clients", "ssh", "console", "bastion", "bastion-host", 
                "admin-jump-host", "jump box", "jump host", "switch", "router"
            ],
            "backup": [
                "backup", "backup-server", "backups", "storage", "archive", "compliance-audit-logger", "audit logger"
            ],
            "application": [
                "application", "app", "apps", "app-server", "backend apps", "microservice", 
                "service", "services", "api", "fraud-analytics-engine", "internal apps"
            ],
            "internet": [
                "internet", "public", "external", "wan", "outside world", "cloud", "outside", 
                "world", "anyone outside", "no one outside", "web outside"
            ],
            "core": [
                "core", "core-router", "core-banking-switch", "med-core-gateway", "backbone", 
                "infrastructure", "switches"
            ],
            "security": [
                "security", "perimeter", "firewall", "border-firewall", "main-firewall", 
                "biomed-firewall", "pci-dss-firewall", "store-firewall", "border"
            ],
            "biomed": [
                "biomed", "medical_iot", "medical devices", "medical iot", "iot-devices", 
                "mri-scanner", "mri", "infusion-pumps", "infusion pump", "infusion pumps", 
                "pacs-imaging-server", "pacs", "biomedical", "medical equipment"
            ],
            "clinical": [
                "clinical", "hospital", "doctors", "doctors-workstations", "icu", 
                "icu-nurses-station", "telemetry", "nurses station", "patient care", "nursing"
            ],
            "banking": [
                "banking", "core_banking", "swift", "swift-transfer-node", "atm", 
                "atm-transaction-switch", "teller-workstations", "teller", "teller stations"
            ],
            "pos": [
                "pos", "pos terminal", "pos terminals", "pos-terminal-01", "pos-terminal-02", 
                "point of sale", "checkout", "cash register", "cashier"
            ],
            "compute": [
                "compute", "k8s", "kubernetes", "k8s control plane", "k8s-control-plane", 
                "control plane", "k8s-worker-node-1", "k8s-worker-node-2", "worker node", 
                "worker nodes", "cluster", "redis", "redis-cache", "cache"
            ],
            "spine": [
                "spine", "spine-switch-01", "spine-switch-02", "spine switches"
            ],
            "leaf": [
                "leaf", "leaf-switch-01", "leaf-switch-02", "leaf-switch-03", "leaf switches"
            ]
        }

    def _get_active_topology_context(self, db) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract active devices, security zones, and subnets from live database if available."""
        if not db:
            return {}, {}
        try:
            from app.models.device import Device
            devices = db.query(Device).all()
            device_map = {}
            zone_map = {}
            for d in devices:
                device_map[d.name.lower()] = d
                if d.zone:
                    z = d.zone.lower()
                    if z not in zone_map:
                        zone_map[z] = []
                    zone_map[z].append(d)
            return device_map, zone_map
        except Exception:
            return {}, {}

    def _resolve_zone(self, text: str, db=None) -> str:
        if not text:
            return text
        t = text.lower().strip()
        t = re.sub(r'^(the|all devices in the|all devices in|all|any|our|internal|external)\s+', '', t).strip()
        t = re.sub(r'\s+(network|devices|zone|servers|server|clients|workstations|dept|department|vlan|systems|machines|traffic|endpoints|cluster|database|db|switch|gateway|terminal|terminals|hub|ap|wifi)$', '', t).strip()

        # 1. Match against active database devices and zones if DB session provided
        device_map, zone_map = self._get_active_topology_context(db)
        if device_map:
            # Check if text directly matches an active device name
            for dev_name, dev in device_map.items():
                if t == dev_name or t in dev_name or dev_name in t:
                    return dev.zone or dev_name
            # Check if text matches an active zone
            for zone_name in zone_map.keys():
                if t == zone_name or t in zone_name or zone_name in t:
                    return zone_name

        # 2. Check direct match with known ontology synonyms
        for standard_zone, synonyms in self.zone_synonyms.items():
            if t == standard_zone or t in synonyms:
                return standard_zone
            for syn in synonyms:
                if syn == t or (len(syn) > 3 and syn in t) or (len(t) > 3 and t in syn):
                    return standard_zone

        return t or text.strip()

    def _resolve_zone_from_cidr(self, cidr: str, db=None) -> str:
        """Infer security zone from IP CIDR prefix or active topology."""
        device_map, _ = self._get_active_topology_context(db)
        for _, dev in device_map.items():
            if dev.subnet and dev.subnet.split('/')[0] in cidr:
                return dev.zone or "internal"

        # Well-known subnets in platform
        if "10.1.30." in cidr or "192.168.40." in cidr or "192.168.130." in cidr:
            return "guest"
        if "10.1.10." in cidr:
            return "hr"
        if "10.1.20." in cidr:
            return "engineering"
        if "10.1.60." in cidr or "192.168.10." in cidr or "10.200.20." in cidr or "172.20.30." in cidr:
            return "database"
        if "10.1.70." in cidr or "172.20.10." in cidr or "10.200.10." in cidr:
            return "dmz"
        if "10.1.40." in cidr or "172.20.40." in cidr or "10.200.50." in cidr:
            return "management"
        if "192.168.20." in cidr:
            return "biomed"
        if "192.168.30." in cidr or "10.200.40." in cidr:
            return "clinical"
        if "192.168.110." in cidr:
            return "pos"
        if "172.20.20." in cidr:
            return "compute"
        return "internal"

    def parse(self, natural_language: str, fallback_on_unrecognized: bool = False, db=None) -> Dict[str, Any]:
        nl = natural_language.lower().strip()
        # Strip trailing punctuation
        nl = re.sub(r'[\.\!\?\;]+$', '', nl).strip()
        
        # Normalize contractions and common conversational filler phrases
        nl = re.sub(r"\bcan't\b", "cannot", nl)
        nl = re.sub(r"\bcant\b", "cannot", nl)
        nl = re.sub(r"\bwon't\b", "will not", nl)
        nl = re.sub(r"\bdon't\b", "do not", nl)
        nl = re.sub(r"\bdont\b", "do not", nl)
        nl = re.sub(r"\bshouldn't\b", "should not", nl)
        nl = re.sub(r"\bdoesn't\b", "does not", nl)
        nl = re.sub(r"^(please\s+|ensure\s+that\s+|ensure\s+|make\s+sure\s+that\s+|make\s+sure\s+|i\s+want\s+to\s+|we\s+need\s+to\s+|command:\s*|rule:\s*|intent:\s*|policy:\s*)", "", nl).strip()

        # Extract ports & protocols
        detected_port = "any"
        detected_proto = "any"
        port_match = re.search(r'\b(?:port\s+|on\s+port\s+)(\d+)\b', nl)
        if port_match:
            detected_port = port_match.group(1)
        if "ssh" in nl or detected_port == "22":
            detected_proto = "tcp"
            detected_port = "22"
        elif "https" in nl or detected_port == "443":
            detected_proto = "tcp"
            detected_port = "443"
        elif "http" in nl or detected_port == "80":
            detected_proto = "tcp"
            detected_port = "80"
        elif "sql" in nl or detected_port in ["3306", "5432"]:
            detected_proto = "tcp"
            detected_port = detected_port if detected_port != "any" else "5432"
        elif "ping" in nl or "icmp" in nl:
            detected_proto = "icmp"

        # -------------------------------------------------------------
        # SPECIAL PATTERN 1: Explicit Subnets / CIDRs
        # e.g., "Block all connections from 10.1.30.0/24 to 10.1.60.0/24"
        # -------------------------------------------------------------
        cidrs = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b', nl)
        if len(cidrs) >= 2:
            src_cidr = cidrs[0]
            dst_cidr = cidrs[1]
            is_deny = any(w in nl for w in ["block", "deny", "isolate", "prevent", "stop", "not", "cannot", "shut", "cut", "no"])
            s_zone = self._resolve_zone_from_cidr(src_cidr, db)
            d_zone = self._resolve_zone_from_cidr(dst_cidr, db)
            return {
                "status": "parsed",
                "confidence": 0.98,
                "policies": [{
                    "policy_type": "isolate" if "isolate" in nl else ("deny" if is_deny else "allow"),
                    "action": "deny" if is_deny else "permit",
                    "source_network": src_cidr,
                    "destination_network": dst_cidr,
                    "source_zone": s_zone,
                    "destination_zone": d_zone,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 2: Inverted Asset Protection ("keep X private from Y", "protect X from Y")
        # In this phrasing: X is the protected asset (DESTINATION), Y is the untrusted source (SOURCE)
        # -------------------------------------------------------------
        inverted_protection_patterns = [
            r'keep\s+(.*?)\s+(?:private|safe|isolated|shielded|protected)\s+from\s+(.*)',
            r'protect\s+(.*?)\s+from\s+(.*)',
            r'shield\s+(.*?)\s+from\s+(.*)',
            r'hide\s+(.*?)\s+from\s+(.*)',
            r'isolate\s+(.*?)\s+from\s+(?:unauthorized\s+access\s+by\s+|all\s+access\s+from\s+)?(.*)'
        ]
        for pat in inverted_protection_patterns:
            m = re.search(pat, nl)
            if m:
                protected_asset = self._resolve_zone(m.group(1), db)
                untrusted_src = self._resolve_zone(m.group(2), db)
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "isolate",
                        "action": "deny",
                        "source_zone": untrusted_src,
                        "destination_zone": protected_asset,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 3: Explicit Directional "From X to Y" (Deny / Shut off / Cut off)
        # -------------------------------------------------------------
        from_to_patterns = [
            r'(?:block|deny|cut\s+off|shut\s+off)\s+(?:all\s+)?(?:connections|traffic|access)?\s*from\s+(.*?)\s+to\s+(.*)',
            r'no\s+access\s+(?:is\s+permitted\s+)?from\s+(.*?)\s+to\s+(.*)',
            r'shut\s+off\s+access\s+from\s+(.*?)\s+to\s+(.*)',
            r'cut\s+off\s+(.*?)\s+from\s+(.*)',
            r'disconnect\s+(.*?)\s+from\s+(.*)',
            r'quarantine\s+(.*?)\s+from\s+(.*)',
            r'ban\s+(.*?)\s+from\s+(?:accessing\s+|reaching\s+)?(.*)'
        ]
        for pat in from_to_patterns:
            m = re.search(pat, nl)
            if m:
                s_zone = self._resolve_zone(m.group(1), db)
                d_zone = self._resolve_zone(m.group(2), db)
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "deny",
                        "action": "deny",
                        "source_zone": s_zone,
                        "destination_zone": d_zone,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 3.5: Compound Internet Access with Internal Denial
        # -------------------------------------------------------------
        if "must have internet access but must not access" in nl or ("internet access" in nl and ("not access" in nl or "cannot access" in nl)):
            m = re.search(r'(.*?)\s+(?:must have internet access but (?:must not|cannot) access|can access internet but cannot access)\s+(.*)', nl)
            if m:
                s_zone = self._resolve_zone(m.group(1), db)
                d_zone = self._resolve_zone(m.group(2), db)
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [
                        {"policy_type": "allow", "action": "permit", "source_zone": s_zone, "destination_zone": "internet", "protocol": "any", "port": "any"},
                        {"policy_type": "deny", "action": "deny", "source_zone": s_zone, "destination_zone": d_zone, "protocol": "any", "port": "any"}
                    ]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 4: Negative Prohibition (Do not allow / Prevent / Stop / Cannot)
        # -------------------------------------------------------------
        prohibition_patterns = [
            # "Do not allow X to reach/touch/access Y"
            r'(?:do\s+not\s+allow|dont\s+allow)\s+(.*?)\s+to\s+(?:touch|reach|access|communicate with|connect to)\s+(.*)',
            # "No one in/from X should be able to reach Y"
            r'no\s+one\s+(?:in|from)?\s+(.*?)\s+should\s+be\s+able\s+to\s+reach\s+(.*)',
            # "Prevent X from accessing/reaching Y"
            r'prevent\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to)\s+(.*)',
            # "Stop X from reaching/accessing Y"
            r'stop\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to)\s+(.*)',
            # "X must not communicate with Y"
            r'(.*?)\s+must\s+not\s+communicate\s+(?:directly\s+)?with\s+(.*)',
            # "X cannot / should not access Y"
            r'(.*?)\s+(?:cannot|must not|should not|may not)\s+(?:access|reach|touch|connect to)\s+(.*)',
            # "X must not access Y directly"
            r'(.*?)\s+must\s+not\s+access\s+(.*?)\s+directly',
            # "Block X from Y"
            r'block\s+(.*?)\s+from\s+(?:reaching|accessing)?\s*(.*)',
            # "X must remain isolated from Y"
            r'(.*?)\s+must\s+remain\s+isolated\s+from\s+(.*)',
            # "Traffic between X and Y must be blocked"
            r'(?:traffic\s+between|connections\s+between)\s+(.*?)\s+and\s+(.*?)\s+must\s+be\s+blocked'
        ]
        for pat in prohibition_patterns:
            m = re.search(pat, nl)
            if m:
                s_zone = self._resolve_zone(m.group(1), db)
                d_zone = self._resolve_zone(m.group(2), db)
                is_isolate = "isolate" in pat or "isolated" in pat or "isolate" in nl or "isolated" in nl
                return {
                    "status": "parsed",
                    "confidence": 0.94,
                    "policies": [{
                        "policy_type": "isolate" if is_isolate else "deny",
                        "action": "deny",
                        "source_zone": s_zone,
                        "destination_zone": d_zone,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 5: Restrictive / Specific Protocol Access
        # e.g., "Only bastion host may access k8s control plane using SSH"
        # -------------------------------------------------------------
        if "only" in nl and ("may access" in nl or "can access" in nl or "is allowed" in nl):
            m = re.search(r'only\s+(.*?)\s+(?:may access|can access|is allowed to access)\s+(.*?)(?:\s+using\s+|\s+via\s+|\s+on\s+port\s+)(.*)', nl)
            if m:
                src = self._resolve_zone(m.group(1), db)
                dst = self._resolve_zone(m.group(2), db)
                proto = m.group(3).strip()
                p_port = "22" if "ssh" in proto.lower() else ("443" if "https" in proto.lower() else "any")
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "restrict",
                        "action": "permit",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": "tcp" if p_port in ["22", "443"] else "any",
                        "port": p_port
                    }]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 6: Allowances / Reachability
        # -------------------------------------------------------------
        allow_patterns = [
            r'allow\s+(.*?)\s+to\s+(?:access|reach|communicate with|connect to)\s+(.*)',
            r'permit\s+(.*?)\s+to\s+(?:access|reach|communicate with|connect to)\s+(.*)',
            r'(.*?)\s+(?:must be able to|can|should be able to)\s+access\s+(.*)',
            r'enable\s+(?:all\s+)?traffic\s+between\s+(.*?)\s+and\s+(.*)'
        ]
        for pat in allow_patterns:
            m = re.search(pat, nl)
            if m:
                s_zone = self._resolve_zone(m.group(1), db)
                d_zone = self._resolve_zone(m.group(2), db)
                return {
                    "status": "parsed",
                    "confidence": 0.92,
                    "policies": [{
                        "policy_type": "allow",
                        "action": "permit",
                        "source_zone": s_zone,
                        "destination_zone": d_zone,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # HEURISTIC 1: Scan for all zones / devices in active DB or Lexicon
        # -------------------------------------------------------------
        device_map, zone_map = self._get_active_topology_context(db)
        found_tokens = []

        # Check active devices
        for d_name, d_obj in device_map.items():
            if d_name in nl:
                found_tokens.append((d_obj.zone or d_name, nl.find(d_name)))

        # Check active zones
        for z_name in zone_map.keys():
            if z_name in nl:
                found_tokens.append((z_name, nl.find(z_name)))

        # Check ontology synonyms
        for std_z, syns in self.zone_synonyms.items():
            for s in syns:
                if re.search(r'\b' + re.escape(s) + r'\b', nl):
                    found_tokens.append((std_z, nl.find(s)))
                    break

        # Deduplicate while preserving earliest appearance order
        seen = set()
        ordered_zones = []
        found_tokens.sort(key=lambda x: x[1])
        for z, idx in found_tokens:
            if z not in seen:
                seen.add(z)
                ordered_zones.append(z)

        is_deny_action = any(w in nl for w in [
            "block", "deny", "isolate", "prevent", "stop", "not", "cannot", "never", 
            "cut", "shut", "ban", "drop", "quarantine", "lockdown", "protect", "shield", "private"
        ])

        if len(ordered_zones) >= 2:
            src = ordered_zones[0]
            dst = ordered_zones[1]
            return {
                "status": "parsed",
                "confidence": 0.90,
                "policies": [{
                    "policy_type": "isolate" if "isolate" in nl else ("deny" if is_deny_action else "allow"),
                    "action": "deny" if is_deny_action else "permit",
                    "source_zone": src,
                    "destination_zone": dst,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        # -------------------------------------------------------------
        # HEURISTIC 2: Single Target Zone Mentioned
        # -------------------------------------------------------------
        if len(ordered_zones) == 1:
            z = ordered_zones[0]
            if is_deny_action:
                # If sensitive asset mentioned, isolate untrusted from it
                if z in ["database", "hr", "backup", "application", "ehr", "cardholder", "vault", "banking", "clinical", "biomed"]:
                    src, dst = "guest", z
                else:
                    src, dst = z, "database"
                return {
                    "status": "parsed",
                    "confidence": 0.85,
                    "assumptions": f"Inferred perimeter security policy: isolate untrusted '{src}' from protected '{dst}'.",
                    "policies": [{
                        "policy_type": "deny",
                        "action": "deny",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }
            else:
                return {
                    "status": "parsed",
                    "confidence": 0.82,
                    "assumptions": f"Inferred outbound internet access for '{z}'.",
                    "policies": [{
                        "policy_type": "allow",
                        "action": "permit",
                        "source_zone": z,
                        "destination_zone": "internet",
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # HEURISTIC 3: Universal Zero-Trust Fallback (Always Produces Clean Policy)
        # -------------------------------------------------------------
        if fallback_on_unrecognized or any(w in nl for w in ["lockdown", "zero trust", "secure", "isolate", "protect", "safe"]):
            # Query active topology to find actual client vs server zones
            src_zone = "guest"
            dst_zone = "database"
            if zone_map:
                all_zones = list(zone_map.keys())
                for cand in ["guest", "wan", "untrusted", "edge", "pos", "clinical", "biomed"]:
                    if cand in all_zones:
                        src_zone = cand
                        break
                for cand in ["database", "hr", "compute", "core", "application", "internal"]:
                    if cand in all_zones and cand != src_zone:
                        dst_zone = cand
                        break

            return {
                "status": "parsed",
                "confidence": 0.80,
                "assumptions": f"Universal Zero-Trust Enforcement: Synthesized perimeter boundary policy ({src_zone} -> {dst_zone}) for: '{natural_language}'.",
                "policies": [{
                    "policy_type": "deny",
                    "action": "deny",
                    "source_zone": src_zone,
                    "destination_zone": dst_zone,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        return {"status": "draft", "confidence": 0.0, "policies": []}
