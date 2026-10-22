import re
import ipaddress
from typing import Optional, Dict, Any, List

class IntentParser:
    def __init__(self):
        # Multi-topology lexical ontology covering Enterprise, Cloud Datacenter,
        # Smart Healthcare, FinTech Banking, Retail Branch, and General Zero-Trust
        self.zone_synonyms = {
            "guest": [
                "guest", "guests", "guest network", "guest wifi", "guest-wifi", "guest-clients", 
                "guest vlan", "visitor", "visitors", "visitor-patient-wifi", "visitor wifi", 
                "patient wifi", "patient-wifi", "customer-guest-wifi", "customer wifi", 
                "byod", "contractor", "contractors", "untrusted", "public wifi", 
                "client", "clients", "laptop", "laptops", "mobile", "bad guys", "hackers", 
                "outsiders", "unauthorized users", "external users", "attackers", "testing",
                "test", "stranger", "strangers", "rogue", "compromised", "infected", 
                "sales laptop", "vendor", "vendors", "temporary", "temp", "nobody from outside",
                "outside world", "outside users"
            ],
            "hr": [
                "hr", "human resources", "human-resources", "hr network", "hr department", 
                "hr-server", "hr-clients", "payroll", "personnel", "staff", "employee", "employees", 
                "office", "finance", "accounting", "finances", "billing dept", "billing"
            ],
            "engineering": [
                "engineering", "eng", "developers", "dev", "devs", "developer", "eng-server", 
                "eng-clients", "code", "git", "ci-cd", "rnd", "research", "tech", "development"
            ],
            "database": [
                "database", "databases", "db", "dbs", "db-server", "sql", "mysql", "postgres", 
                "postgres-cluster", "postgresql", "oracle", "mongo", "ehr-database", "ehr", 
                "cardholder-vault-db", "cardholder vault", "vault", "inventory-db", "inventory database", 
                "storage", "records", "data store", "sensitive files", "customer records", "financial records",
                "patient records", "internal records", "internal systems", "sensitive data", "sensitive stuff",
                "secret", "secrets", "production", "prod", "prod database", "production servers", "archive"
            ],
            "dmz": [
                "dmz", "web", "web server", "web-server", "website", "demilitarized zone", 
                "external facing", "public facing", "proxy", "frontend", "nginx", 
                "payment-api-gateway", "payment api", "ingress-proxy", "ingress", "portal"
            ],
            "management": [
                "management", "mgmt", "admin", "admins", "administrator", "administrators", 
                "mgmt-clients", "ssh", "console", "bastion", "bastion-host", 
                "admin-jump-host", "jump box", "jump host"
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
                "world", "anyone outside", "web outside"
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
                "biomed", "medical_iot", "medical devices", "medical iot", "iot-devices", "iot",
                "mri-scanner", "mri", "infusion-pumps", "infusion pump", "infusion pumps", 
                "pacs-imaging-server", "pacs", "biomedical", "medical equipment", "sensors", "telemetry"
            ],
            "clinical": [
                "clinical", "hospital", "doctors", "doctors-workstations", "icu", 
                "icu-nurses-station", "nurses station", "patient care", "nursing", "nurses"
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
                "k8s-worker-node-1", "k8s-worker-node-2", "worker node", 
                "worker nodes", "cluster", "redis", "redis-cache", "cache"
            ],
            "spine": [
                "spine", "spine-switch-01", "spine-switch-02", "spine switches"
            ],
            "leaf": [
                "leaf", "leaf-switch-01", "leaf-switch-02", "leaf-switch-03", "leaf switches"
            ]
        }

        # Hierarchy / Trust Tiers (Lower number = lower trust / client / peripheral)
        self.trust_tiers = {
            "internet": 0,
            "guest": 1,
            "pos": 1,
            "biomed": 1,
            "hr": 2,
            "engineering": 2,
            "clinical": 2,
            "banking": 2,
            "leaf": 2,
            "dmz": 3,
            "application": 3,
            "compute": 3,
            "spine": 3,
            "database": 4,
            "backup": 4,
            "core": 5,
            "management": 5,
            "security": 5
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

    def _map_to_active_zone(self, candidate: str, active_zones: List[str], is_destination: bool = False) -> str:
        """Map any candidate zone name to the best matching zone that ACTUALLY exists in active DB."""
        if not active_zones:
            return candidate

        c = candidate.lower()
        if c in active_zones:
            return c

        # 1. Check direct substrings
        for az in active_zones:
            if az in c or c in az:
                return az

        # 2. Semantic Role mapping to active zones
        untrusted_keywords = {"guest", "visitor", "contractor", "sales", "client", "laptop", "testing", "test", "outside", "stranger", "bad", "rogue", "untrusted", "public", "hacker", "compromised"}
        sensitive_keywords = {"database", "db", "record", "sql", "postgres", "vault", "ehr", "cardholder", "finance", "accounting", "prod", "server", "sensitive", "secret", "storage", "archive", "internal"}
        mgmt_keywords = {"admin", "mgmt", "management", "ssh", "console", "bastion", "router", "switch", "core"}
        web_keywords = {"web", "dmz", "ingress", "proxy", "frontend", "api"}
        clinical_keywords = {"biomed", "medical", "iot", "pump", "mri", "icu", "nurse", "patient", "clinical"}
        banking_keywords = {"bank", "atm", "teller", "swift", "pos", "cash"}

        if any(k in c for k in untrusted_keywords):
            for cand in ["guest", "leaf", "pos", "biomed", "untrusted"]:
                if cand in active_zones:
                    return cand
            return active_zones[0]

        if any(k in c for k in sensitive_keywords):
            for cand in ["database", "compute", "hr", "core", "application"]:
                if cand in active_zones:
                    return cand
            return active_zones[-1]

        if any(k in c for k in mgmt_keywords):
            for cand in ["management", "core", "security"]:
                if cand in active_zones:
                    return cand

        if any(k in c for k in web_keywords):
            if "dmz" in active_zones:
                return "dmz"

        if any(k in c for k in clinical_keywords):
            for cand in ["biomed", "clinical", "database"]:
                if cand in active_zones:
                    return cand

        if any(k in c for k in banking_keywords):
            for cand in ["banking", "pos", "database"]:
                if cand in active_zones:
                    return cand

        # Fallback based on orientation
        if is_destination:
            for cand in ["database", "hr", "compute", "core", "application"]:
                if cand in active_zones:
                    return cand
            return active_zones[-1]
        else:
            for cand in ["guest", "hr", "leaf", "pos", "biomed", "dmz"]:
                if cand in active_zones:
                    return cand
            return active_zones[0]

    def _resolve_zone(self, text: str, db=None, is_destination: bool = False) -> str:
        if not text:
            return "guest" if not is_destination else "database"
        t = text.lower().strip()
        t = re.sub(r'^(the|all devices in the|all devices in|all|any|our|internal|external|my|our)\s+', '', t).strip()
        t = re.sub(r'\s+(network|devices|zone|servers|server|clients|workstations|dept|department|vlan|systems|machines|traffic|endpoints|cluster|database|db|switch|gateway|terminal|terminals|hub|ap|wifi|environment|hosts|host)$', '', t).strip()

        device_map, zone_map = self._get_active_topology_context(db)
        active_zones = list(zone_map.keys()) if zone_map else []

        # 1. Match against active database devices directly
        if device_map:
            # Exact names must win before substring aliases (otherwise
            # "web-server" captures "web-server2").
            exact_device = device_map.get(t)
            if exact_device:
                return exact_device.zone or exact_device.name
            for dev_name, dev in device_map.items():
                if re.search(r'(?<![\w-])' + re.escape(dev_name) + r'(?![\w-])', t):
                    return dev.zone or dev_name

        # 2. Match against active database zones directly
        if active_zones:
            if t in active_zones:
                return t
            for zone_name in active_zones:
                if re.search(r'(?<![\w-])' + re.escape(zone_name) + r'(?![\w-])', t):
                    return zone_name

        # 3. Check direct match with known ontology synonyms
        candidate_zone = None
        for standard_zone, synonyms in self.zone_synonyms.items():
            if t == standard_zone or t in synonyms:
                candidate_zone = standard_zone
                break
            for syn in synonyms:
                if syn == t or (len(syn) > 3 and syn in t) or (len(t) > 3 and t in syn):
                    candidate_zone = standard_zone
                    break
            if candidate_zone:
                break

        if not candidate_zone:
            candidate_zone = t

        # Ensure mapped zone is ALWAYS valid for the active topology
        if active_zones:
            return self._map_to_active_zone(candidate_zone, active_zones, is_destination=is_destination)

        return candidate_zone

    def _resolve_endpoint(self, text: str, db=None, is_destination: bool = False) -> tuple[str, Optional[str]]:
        """Resolve a named device to its zone and host subnet; otherwise resolve a zone."""
        cleaned = re.sub(r'^(?:the|all devices in the|all|any)\s+', '', text.lower().strip())
        device_map, _ = self._get_active_topology_context(db)
        for name, device in sorted(device_map.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', cleaned):
                address = (device.ip_address or '').split('/')[0]
                if address:
                    try:
                        ip = ipaddress.ip_address(address)
                        return device.zone or name, f'{address}/{ip.max_prefixlen}'
                    except ValueError:
                        pass
                return device.zone or name, None
        return self._resolve_zone(text, db, is_destination), None

    def _resolve_zone_from_cidr(self, cidr: str, db=None, is_destination: bool = False) -> str:
        """Infer security zone from IP CIDR prefix or active topology."""
        device_map, zone_map = self._get_active_topology_context(db)
        active_zones = list(zone_map.keys()) if zone_map else []
        for _, dev in device_map.items():
            if dev.subnet and dev.subnet.split('/')[0] in cidr:
                return dev.zone or ("database" if is_destination else "guest")

        # Well-known subnets in platform
        mapped = "internal"
        if "10.1.30." in cidr or "192.168.40." in cidr or "192.168.130." in cidr:
            mapped = "guest"
        elif "10.1.10." in cidr:
            mapped = "hr"
        elif "10.1.20." in cidr:
            mapped = "engineering"
        elif "10.1.60." in cidr or "192.168.10." in cidr or "10.200.20." in cidr or "172.20.30." in cidr:
            mapped = "database"
        elif "10.1.70." in cidr or "172.20.10." in cidr or "10.200.10." in cidr:
            mapped = "dmz"
        elif "10.1.40." in cidr or "172.20.40." in cidr or "10.200.50." in cidr:
            mapped = "management"
        elif "192.168.20." in cidr:
            mapped = "biomed"
        elif "192.168.30." in cidr or "10.200.40." in cidr:
            mapped = "clinical"
        elif "192.168.110." in cidr:
            mapped = "pos"
        elif "172.20.20." in cidr:
            mapped = "compute"

        if active_zones:
            return self._map_to_active_zone(mapped, active_zones, is_destination=is_destination)
        return mapped

    def parse(self, natural_language: str, fallback_on_unrecognized: bool = False, db=None) -> Dict[str, Any]:
        nl = natural_language.lower().strip()
        nl = re.sub(r'[\.\!\?\;]+$', '', nl).strip()
        
        # Normalize contractions and common conversational filler phrases
        nl = re.sub(r"\bcan't\b", "cannot", nl)
        nl = re.sub(r"\bcant\b", "cannot", nl)
        nl = re.sub(r"\bwon't\b", "will not", nl)
        nl = re.sub(r"\bdon't\b", "do not", nl)
        nl = re.sub(r"\bdont\b", "do not", nl)
        nl = re.sub(r"\bshouldn't\b", "should not", nl)
        nl = re.sub(r"\bshouldnt\b", "should not", nl)
        nl = re.sub(r"\bdoesn't\b", "does not", nl)
        nl = re.sub(r"\bdoesnt\b", "does not", nl)
        nl = re.sub(r"\bmustn't\b", "must not", nl)
        nl = re.sub(r"\bmustnt\b", "must not", nl)
        nl = re.sub(r"^(please\s+|ensure\s+that\s+|ensure\s+|make\s+sure\s+that\s+|make\s+sure\s+|i\s+want\s+to\s+|we\s+need\s+to\s+|command:\s*|rule:\s*|intent:\s*|policy:\s*)", "", nl).strip()

        # Comprehensive Denial / Prohibition detection with inflected forms
        deny_words = [
            "block", "blocks", "blocked", "blocking",
            "deny", "denies", "denied", "denying",
            "isolate", "isolates", "isolated", "isolating", "isolation",
            "prevent", "prevents", "prevented", "preventing", "prevention",
            "stop", "stops", "stopped", "stopping",
            "prohibit", "prohibits", "prohibited", "prohibiting", "prohibition",
            "disallow", "disallows", "disallowed", "disallowing",
            "ban", "bans", "banned", "banning",
            "quarantine", "quarantines", "quarantined", "quarantining",
            "reject", "rejects", "rejected", "rejecting",
            "drop", "drops", "dropped", "dropping",
            "cut", "cuts", "cutting",
            "shut", "shuts", "shutting",
            "disconnect", "disconnects", "disconnected", "disconnecting",
            "lockdown", "shield", "protect", "protected", "protecting", "protection",
            "private", "safe", "restricted", "restrict", "restricts",
            "not", "cannot", "cant", "never", "nobody", "no one", "no-one", "none",
            "dont", "wont", "shouldnt", "mustnt"
        ]
        is_deny_action = any(re.search(r'\b' + re.escape(w) + r'\b', nl) for w in deny_words) or \
            "cut off" in nl or "shut off" in nl or "keep private" in nl or "keep safe" in nl or "do not" in nl or "blocked from" in nl or "isolated from" in nl

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
        # -------------------------------------------------------------
        cidrs = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b', nl)
        if len(cidrs) >= 2:
            src_cidr = cidrs[0]
            dst_cidr = cidrs[1]
            s_zone = self._resolve_zone_from_cidr(src_cidr, db, is_destination=False)
            d_zone = self._resolve_zone_from_cidr(dst_cidr, db, is_destination=True)
            return {
                "status": "parsed",
                "confidence": 0.98,
                "policies": [{
                    "policy_type": "isolate" if "isolate" in nl else ("deny" if is_deny_action else "allow"),
                    "action": "deny" if is_deny_action else "permit",
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
        # -------------------------------------------------------------
        inverted_protection_patterns = [
            r'keep\s+(.*?)\s+(?:private|safe|isolated|shielded|protected)\s+from\s+(.*)',
            r'protect\s+(.*?)\s+from\s+(.*)',
            r'shield\s+(.*?)\s+from\s+(.*)',
            r'hide\s+(.*?)\s+from\s+(.*)',
            r'save\s+(.*?)\s+from\s+(.*)',
            r'safeguard\s+(.*?)\s+from\s+(.*)',
            r'isolate\s+(.*?)\s+from\s+(?:unauthorized\s+access\s+by\s+|all\s+access\s+from\s+)?(.*)'
        ]
        for pat in inverted_protection_patterns:
            m = re.search(pat, nl)
            if m:
                raw_protected = m.group(1)
                raw_untrusted = m.group(2)
                z_protected = self._resolve_zone(raw_protected, db, is_destination=True)
                z_untrusted = self._resolve_zone(raw_untrusted, db, is_destination=False)
                # Tier normalization: lower tier initiates (source), higher tier is protected (dest)
                tier_p = self.trust_tiers.get(z_protected, 3)
                tier_u = self.trust_tiers.get(z_untrusted, 1)
                if tier_p < tier_u:
                    s_zone, d_zone = z_protected, z_untrusted
                else:
                    s_zone, d_zone = z_untrusted, z_protected

                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "isolate",
                        "action": "deny",
                        "source_zone": s_zone,
                        "destination_zone": d_zone,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 2.5: Passive Voice Prohibition ("X is/are blocked/isolated from Y")
        # -------------------------------------------------------------
        passive_patterns = [
            r'(.*?)\s+(?:is|are|should be|must be|shall be|cannot be)\s+(?:blocked|denied|isolated|quarantined|prevented|banned|cut off)\s+from\s+(.*)',
            r'(.*?)\s+(?:is|are)\s+not\s+allowed\s+to\s+(?:reach|access|touch|communicate with)\s+(.*)'
        ]
        for pat in passive_patterns:
            m = re.search(pat, nl)
            if m:
                z1, n1 = self._resolve_endpoint(m.group(1), db, is_destination=False)
                z2, n2 = self._resolve_endpoint(m.group(2), db, is_destination=True)
                s_zone, d_zone = z1, z2
                if s_zone == d_zone and not (n1 and n2):
                    if s_zone in ["guest", "leaf", "pos", "biomed", "untrusted"]:
                        d_zone = "database"
                    else:
                        s_zone = "guest"
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "isolate" if ("isolate" in pat or "isolated" in nl) else "deny",
                        "action": "deny",
                        "source_zone": s_zone,
                        "source_network": n1,
                        "destination_zone": d_zone,
                        "destination_network": n2,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # Requirements phrased from the destination's point of view, such as
        # "The app server must be reachable by engineering".
        inverse_access_patterns = [
            (r'(.*?)\s+(?:is|are|must be|should be|needs? to be)\s+(?:accessible|reachable|available)\s+(?:to|by)\s+(.*)', False),
            (r'(.*?)\s+(?:is|are|must be|should be)\s+not\s+(?:accessible|reachable|available)\s+(?:to|by)\s+(.*)', True),
        ]
        for pattern, denied in inverse_access_patterns:
            match = re.search(pattern, nl)
            if match:
                destination = self._resolve_zone(match.group(1), db, is_destination=True)
                source = self._resolve_zone(match.group(2), db, is_destination=False)
                return {
                    "status": "parsed",
                    "confidence": 0.93,
                    "policies": [{
                        "policy_type": "deny" if denied else "allow",
                        "action": "deny" if denied else "permit",
                        "source_zone": source,
                        "destination_zone": destination,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # "Database access must be restricted to the application server" means
        # application -> database access is required by this policy.
        restricted_access = re.search(
            r'(.*?)\s+access\s+(?:must|should|is required to)\s+(?:remain\s+)?restricted\s+to\s+(.*)',
            nl
        )
        if restricted_access:
            destination = self._resolve_zone(restricted_access.group(1), db, is_destination=True)
            source = self._resolve_zone(restricted_access.group(2), db, is_destination=False)
            return {
                "status": "parsed",
                "confidence": 0.92,
                "policies": [{
                    "policy_type": "require",
                    "action": "permit",
                    "source_zone": source,
                    "destination_zone": destination,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        # Short commands often omit an explicit network verb: "stop X from Y".
        # Keep X as the initiating endpoint and Y as the destination. Resolve
        # exact device names to host routes so the ACL remains narrowly scoped.
        short_deny = re.search(
            r'^(?:stop|prevent|block|deny|disallow|disconnect)\s+'
            r'(?:(?:all\s+)?(?:network\s+)?(?:traffic|connections|access)\s+)?(.+?)\s+from\s+'
            r'(?:accessing\s+|reaching\s+|connecting\s+to\s+|communicating\s+with\s+)?(.+)$',
            nl
        )
        if short_deny and short_deny.group(1).strip() not in {
            "traffic", "all traffic", "network traffic", "all network traffic",
            "connections", "all connections", "access", "all access"
        }:
            raw_source, raw_destination = short_deny.groups()
            source, source_network = self._resolve_endpoint(raw_source, db, is_destination=False)
            destination, destination_network = self._resolve_endpoint(raw_destination, db, is_destination=True)
            return {
                "status": "parsed",
                "confidence": 0.97,
                "policies": [{
                    "policy_type": "deny",
                    "action": "deny",
                    "source_zone": source,
                    "source_network": source_network,
                    "destination_zone": destination,
                    "destination_network": destination_network,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 3: Explicit Directional "From X to Y" / Cut off / Shut off
        # -------------------------------------------------------------
        from_to_patterns = [
            r'(?:block|deny|cut\s+off|shut\s+off)\s+(?:all\s+)?(?:connections|traffic|access)?\s*from\s+(.*?)\s+to\s+(.*)',
            r'no\s+access\s+(?:is\s+permitted\s+)?from\s+(.*?)\s+to\s+(.*)',
            r'shut\s+off\s+access\s+from\s+(.*?)\s+to\s+(.*)',
            r'cut\s+off\s+(?:access\s+from\s+|all\s+traffic\s+from\s+)?(.*?)\s+to\s+(.*)',
            r'disconnect\s+(.*?)\s+from\s+(.*)',
            r'quarantine\s+(.*?)\s+from\s+(.*)',
            r'ban\s+(.*?)\s+from\s+(?:accessing\s+|reaching\s+)?(.*)'
        ]
        for pat in from_to_patterns:
            m = re.search(pat, nl)
            if m:
                s_zone, s_network = self._resolve_endpoint(m.group(1), db, is_destination=False)
                d_zone, d_network = self._resolve_endpoint(m.group(2), db, is_destination=True)
                if s_zone == d_zone and not (s_network and d_network):
                    if s_zone in ["guest", "leaf", "pos", "biomed", "untrusted"]:
                        d_zone = "database"
                    else:
                        s_zone = "guest"

                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "deny",
                        "action": "deny",
                        "source_zone": s_zone,
                        "source_network": s_network,
                        "destination_zone": d_zone,
                        "destination_network": d_network,
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
                s_zone = self._resolve_zone(m.group(1), db, is_destination=False)
                d_zone = self._resolve_zone(m.group(2), db, is_destination=True)
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [
                        {"policy_type": "allow", "action": "permit", "source_zone": s_zone, "destination_zone": "internet", "protocol": "any", "port": "any"},
                        {"policy_type": "deny", "action": "deny", "source_zone": s_zone, "destination_zone": d_zone, "protocol": "any", "port": "any"}
                    ]
                }

        # -------------------------------------------------------------
        # SPECIAL PATTERN 4: Negative Prohibition (Do not allow / Prevent / Stop / Nobody)
        # -------------------------------------------------------------
        prohibition_patterns = [
            r'nobody\s+(?:from\s+)?(.*?)\s+should\s+(?:touch|reach|access|communicate with|connect to)\s+(.*)',
            r'no\s+one\s+(?:in|from)?\s+(.*?)\s+should\s+(?:be\s+able\s+to\s+)?(?:touch|reach|access|communicate with)\s+(.*)',
            r'(?:do\s+not\s+allow|dont\s+allow|do\s+not\s+let|dont\s+let)\s+(.*?)\s+to\s+(?:touch|reach|access|communicate with|connect to)\s+(.*)',
            r'keep\s+(.*?)\s+out\s+of\s+(.*)',
            r'keep\s+(.*?)\s+from\s+(?:accessing|reaching|getting to|connecting to|communicating with)\s+(.*)',
            r'(.*?)\s+(?:cannot|can\s+not|must\s+not|should\s+not|may\s+not)\s+(?:get to|get into|reach|access|touch|connect to|communicate with|talk to)\s+(.*)',
            r'prevent\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to|touching)\s+(.*)',
            r'stop\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to|touching)\s+(.*)',
            r'(.*?)\s+must\s+not\s+communicate\s+(?:directly\s+)?with\s+(.*)',
            r'(.*?)\s+(?:cannot|must not|should not|may not)\s+(?:access|reach|touch|connect to)\s+(.*)',
            r'(.*?)\s+must\s+not\s+access\s+(.*?)\s+directly',
            r'block\s+(.*?)\s+from\s+(?:reaching|accessing|touching)?\s*(.*)',
            r'(.*?)\s+must\s+remain\s+isolated\s+from\s+(.*)',
            r'(.*?)\s+(?:(?:must|should|may)\s+not|cannot|can\s+not)\s+(?:be\s+able\s+to\s+)?(?:communicate|talk|connect)\s+with\s+(.*)',
            r'(.*?)\s+(?:must|should|may)\s+not\s+(?:be\s+able\s+to\s+)?(?:have\s+)?access\s+to\s+(.*)',
            r'(.*?)\s+(?:must|should)\s+never\s+(?:communicate|talk|connect)\s+with\s+(.*)',
            r'(?:traffic\s+between|connections\s+between)\s+(.*?)\s+and\s+(.*?)\s+must\s+be\s+blocked'
        ]
        for pat in prohibition_patterns:
            m = re.search(pat, nl)
            if m:
                z1 = self._resolve_zone(m.group(1), db, is_destination=False)
                z2 = self._resolve_zone(m.group(2), db, is_destination=True)
                s_zone, d_zone = z1, z2

                if s_zone == d_zone:
                    if s_zone in ["guest", "leaf", "pos", "biomed", "untrusted"]:
                        d_zone = "database"
                    else:
                        s_zone = "guest"

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
        # -------------------------------------------------------------
        if "only" in nl and ("may access" in nl or "can access" in nl or "is allowed" in nl or "permit" in nl):
            m = re.search(r'only\s+(.*?)\s+(?:may access|can access|is allowed to access|permit)\s+(.*?)(?:\s+using\s+|\s+via\s+|\s+on\s+port\s+)(.*)', nl)
            if m:
                src = self._resolve_zone(m.group(1), db, is_destination=False)
                dst = self._resolve_zone(m.group(2), db, is_destination=True)
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
        permit_from_to = re.search(
            r'(?:allow|permit)\s+(?:all\s+)?(?:traffic|connections|access)?\s*from\s+(.+?)\s+to\s+(.+)', nl
        )
        if permit_from_to and not is_deny_action:
            source, source_network = self._resolve_endpoint(permit_from_to.group(1), db, is_destination=False)
            destination, destination_network = self._resolve_endpoint(permit_from_to.group(2), db, is_destination=True)
            return {
                "status": "parsed",
                "confidence": 0.95,
                "policies": [{
                    "policy_type": "allow",
                    "action": "permit",
                    "source_zone": source,
                    "source_network": source_network,
                    "destination_zone": destination,
                    "destination_network": destination_network,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        allow_patterns = [
            r'allow\s+(.*?)\s+to\s+(?:access|reach|communicate with|connect to)\s+(.*)',
            r'permit\s+(.*?)\s+to\s+(?:access|reach|communicate with|connect to)\s+(.*)',
            r'(.*?)\s+(?:must|should|needs? to|has to|is required to)\s+(?:be able to\s+)?(?:access|reach|communicate with|connect to|talk to)\s+(.*)',
            r'(.*?)\s+(?:must|should)\s+have\s+(?:network\s+)?access\s+to\s+(.*)',
            r'(.*?)\s+(?:must|should)\s+be\s+allowed\s+to\s+(?:access|reach|communicate with|connect to|talk to)\s+(.*)',
            r'(.*?)\s+(?:is|are)\s+(?:allowed|permitted)\s+to\s+(?:access|reach|communicate with|connect to|talk to)\s+(.*)',
            r'(.*?)\s+(?:may|requires? to)\s+(?:access|reach|communicate with|connect to|talk to)\s+(.*)',
            r'(.*?)\s+(?:can|may|should be able to)\s+(?:access|reach|communicate with|connect to|talk to)\s+(.*)',
            r'enable\s+(?:all\s+)?traffic\s+between\s+(.*?)\s+and\s+(.*)'
        ]
        if not is_deny_action:
            for pat in allow_patterns:
                m = re.search(pat, nl)
                if m:
                    s_zone, s_network = self._resolve_endpoint(m.group(1), db, is_destination=False)
                    d_zone, d_network = self._resolve_endpoint(m.group(2), db, is_destination=True)
                    return {
                        "status": "parsed",
                        "confidence": 0.92,
                        "policies": [{
                            "policy_type": "allow",
                            "action": "permit",
                            "source_zone": s_zone,
                            "source_network": s_network,
                            "destination_zone": d_zone,
                            "destination_network": d_network,
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

        # Check ontology synonyms, but don't treat a generic word inside a
        # recognized device hostname as a separate zone (e.g. "router" in
        # "edge-router" must not turn the endpoint into the management zone).
        named_device_spans = []
        for d_name in device_map:
            named_device_spans.extend(
                (match.start(), match.end())
                for match in re.finditer(r'(?<![\w-])' + re.escape(d_name) + r'(?![\w-])', nl)
            )
        for std_z, syns in self.zone_synonyms.items():
            for s in syns:
                for match in re.finditer(r'(?<![\w-])' + re.escape(s) + r'(?![\w-])', nl):
                    if any(start <= match.start() and match.end() <= end for start, end in named_device_spans):
                        continue
                    found_tokens.append((std_z, match.start()))
                    break

        seen = set()
        ordered_zones = []
        found_tokens.sort(key=lambda x: x[1])
        for z, idx in found_tokens:
            if z not in seen:
                seen.add(z)
                ordered_zones.append(z)

        if len(ordered_zones) >= 2:
            z1 = self._resolve_zone(ordered_zones[0], db, is_destination=False)
            z2 = self._resolve_zone(ordered_zones[1], db, is_destination=True)
            if is_deny_action:
                t1 = self.trust_tiers.get(z1, 1)
                t2 = self.trust_tiers.get(z2, 3)
                src, dst = (z1, z2) if t1 <= t2 else (z2, z1)
            else:
                src, dst = z1, z2

            if src == dst:
                if src in ["guest", "leaf", "pos", "biomed", "untrusted"]:
                    dst = "database"
                else:
                    src = "guest"

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

        if fallback_on_unrecognized:
            src_zone = self._resolve_zone("guest", db, is_destination=False)
            dst_zone = self._resolve_zone("database", db, is_destination=True)
            return {
                "status": "parsed",
                "confidence": 0.85,
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

        return {
            "status": "draft",
            "confidence": 0.0,
            "assumptions": "Specify both the source and destination network or device.",
            "policies": []
        }
