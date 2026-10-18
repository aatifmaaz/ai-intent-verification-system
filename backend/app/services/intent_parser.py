import re

class IntentParser:
    def __init__(self):
        # Known zones and common synonyms / aliases
        self.zone_synonyms = {
            "guest": [
                "guest", "guests", "guest network", "guest wifi", "guest-wifi", "guest-clients", 
                "guest vlan", "visitor", "visitors", "byod", "contractor", "contractors", 
                "untrusted", "public wifi", "client", "clients", "laptop", "laptops", "mobile"
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
                "oracle", "mongo", "data store", "storage", "records", "data"
            ],
            "dmz": [
                "dmz", "web", "web server", "web-server", "website", "demilitarized zone", 
                "external facing", "public facing", "proxy", "frontend", "nginx"
            ],
            "management": [
                "management", "mgmt", "admin", "admins", "administrator", "administrators", 
                "mgmt-clients", "control plane", "ssh", "console", "bastion", "switch", "router"
            ],
            "backup": [
                "backup", "backup-server", "backups", "storage", "archive", "vault", "recovery"
            ],
            "application": [
                "application", "app", "apps", "app-server", "backend apps", "microservice", "service", "services", "api"
            ],
            "internet": [
                "internet", "public", "external", "wan", "outside world", "cloud", "outside", "world"
            ],
            "core": [
                "core", "core-router", "backbone", "infrastructure", "switches"
            ]
        }
        
    def _resolve_zone(self, text: str) -> str:
        if not text:
            return text
        t = text.lower().strip()
        t = re.sub(r'^(the|all devices in the|all devices in|all|any|our|internal)\s+', '', t).strip()
        t = re.sub(r'\s+(network|devices|zone|servers|server|clients|workstations|dept|department|vlan|systems|machines|traffic|endpoints)$', '', t).strip()
        
        # Check direct match with known synonyms
        for standard_zone, synonyms in self.zone_synonyms.items():
            if t == standard_zone or t in synonyms:
                return standard_zone
            for syn in synonyms:
                if syn in t or t in syn:
                    return standard_zone
        return t or text.strip()

    def parse(self, natural_language: str, fallback_on_unrecognized: bool = False):
        nl = natural_language.lower().strip()
        # Strip trailing punctuation
        nl = re.sub(r'[\.\!\?\;]+$', '', nl).strip()
        
        # Normalize contractions and common filler phrases
        nl = re.sub(r"\bcan't\b", "cannot", nl)
        nl = re.sub(r"\bcant\b", "cannot", nl)
        nl = re.sub(r"\bwon't\b", "will not", nl)
        nl = re.sub(r"\bdon't\b", "do not", nl)
        nl = re.sub(r"\bshouldn't\b", "should not", nl)
        nl = re.sub(r"^(please\s+|ensure\s+that\s+|ensure\s+|make\s+sure\s+that\s+|make\s+sure\s+|i\s+want\s+to\s+|we\s+need\s+to\s+|command:\s*|rule:\s*|intent:\s*)", "", nl).strip()

        # Check for explicit IP addresses (e.g. 10.1.30.100 -> guest, 10.1.10.5 -> hr)
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', nl)
        ip_zone_map = {
            "10.1.30": "guest",
            "10.1.10": "hr",
            "10.1.20": "engineering",
            "10.1.60": "database",
            "10.1.70": "dmz",
            "10.1.40": "management",
            "10.1.80": "backup",
            "10.1.50": "application",
            "10.0.0": "core"
        }
        detected_ip_zones = []
        for ip in ips:
            prefix = ".".join(ip.split(".")[:3])
            if prefix in ip_zone_map:
                detected_ip_zones.append(ip_zone_map[prefix])

        # Detect ports & protocol
        detected_port = "any"
        detected_proto = "any"
        port_match = re.search(r'\b(?:port\s+|on\s+port\s+)(\d+)\b', nl)
        if port_match:
            detected_port = port_match.group(1)
        if "ssh" in nl or detected_port == "22":
            detected_proto = "tcp"
            detected_port = "22"
        elif "http" in nl or detected_port == "80":
            detected_proto = "tcp"
            detected_port = "80"
        elif "https" in nl or detected_port == "443":
            detected_proto = "tcp"
            detected_port = "443"
        elif "sql" in nl or detected_port == "3306":
            detected_proto = "tcp"
            detected_port = "3306"
        elif "ping" in nl or "icmp" in nl:
            detected_proto = "icmp"

        # Complex rule: Internet access but no internal access
        if "must have internet access but must not access" in nl or ("internet access" in nl and ("not access" in nl or "cannot access" in nl)):
            m = re.search(r'(.*?)\s+(?:must have internet access but (?:must not|cannot) access|can access internet but cannot access)\s+(.*)', nl)
            if m:
                s_zone = self._resolve_zone(m.group(1))
                d_zone = self._resolve_zone(m.group(2))
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [
                        {"policy_type": "allow", "action": "permit", "source_zone": s_zone, "destination_zone": "internet", "protocol": "any", "port": "any"},
                        {"policy_type": "deny", "action": "deny", "source_zone": s_zone, "destination_zone": d_zone, "protocol": "any", "port": "any"}
                    ]
                }

        # Restrict with protocol (e.g., only management may access core using SSH)
        if "only" in nl and ("may access" in nl or "can access" in nl) and "using" in nl:
            m = re.search(r'only\s+(.*?)\s+(?:may access|can access)\s+(.*?)\s+using\s+(.*)', nl)
            if m:
                src = self._resolve_zone(m.group(1))
                dst = self._resolve_zone(m.group(2))
                proto = m.group(3).strip()
                return {
                    "status": "parsed",
                    "confidence": 0.92,
                    "policies": [{
                        "policy_type": "restrict",
                        "action": "permit",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": proto,
                        "port": "22" if "ssh" in proto.lower() else "any"
                    }]
                }

        # DENY / ISOLATE / BLOCK PATTERNS
        deny_patterns = [
            # "block traffic between X and Y"
            r'block\s+(?:all\s+)?traffic\s+between\s+(.*?)\s+and\s+(.*)',
            # "block X from Y" or "block X to Y"
            r'block\s+(.*?)\s+(?:from(?:\s+reaching|\s+accessing)?|to)\s+(.*)',
            # "isolate X from Y"
            r'isolate\s+(.*?)\s+from\s+(.*)',
            # "X must remain isolated from Y"
            r'(.*?)\s+must\s+remain\s+isolated\s+from\s+(.*)',
            # "X must not communicate with Y"
            r'(.*?)\s+must\s+not\s+communicate\s+with\s+(.*)',
            # "X cannot communicate with Y" / "X cannot talk to Y"
            r'(.*?)\s+(?:cannot|should not|must not|do not allow to)\s+(?:communicate with|talk to|connect to)\s+(.*)',
            # "X cannot access Y" / "X must not access Y" / "X should not access Y"
            r'(.*?)\s+(?:cannot|must not|should not)\s+access\s+(.*)',
            # "prevent X from accessing Y" / "prevent X from reaching Y"
            r'prevent\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to)\s+(.*)',
            # "stop X from accessing Y" / "stop X from reaching Y"
            r'stop\s+(.*?)\s+from\s+(?:accessing|reaching|communicating with|talking to|connecting to)\s+(.*)',
            # "deny X access to Y"
            r'deny\s+(.*?)(?:\s+access)?\s+to\s+(.*)',
            # "disallow X to access Y"
            r'disallow\s+(.*?)\s+to\s+(?:access|reach)\s+(.*)',
            # "X cannot reach Y" / "X should not reach Y"
            r'(.*?)\s+(?:cannot|should not|must not)\s+reach\s+(.*)',
            # "cut off X from Y"
            r'cut\s+off\s+(.*?)\s+from\s+(.*)',
            # "disconnect X from Y"
            r'disconnect\s+(.*?)\s+from\s+(.*)',
            # "quarantine X from Y"
            r'quarantine\s+(.*?)\s+from\s+(.*)',
            # "drop traffic from X to Y"
            r'drop\s+(?:all\s+)?traffic\s+from\s+(.*?)\s+to\s+(.*)'
        ]

        for pat in deny_patterns:
            m = re.search(pat, nl)
            if m:
                src = self._resolve_zone(m.group(1))
                dst = self._resolve_zone(m.group(2))
                is_isolate = "isolate" in pat or "isolated" in pat
                return {
                    "status": "parsed",
                    "confidence": 0.95,
                    "policies": [{
                        "policy_type": "isolate" if is_isolate else "deny",
                        "action": "deny",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # ALLOW / REACHABLE PATTERNS
        allow_patterns = [
            # "allow X to access Y" / "allow X to reach Y"
            r'allow\s+(.*?)\s+to\s+(?:access|reach|communicate with|connect to)\s+(.*)',
            # "permit X to access Y"
            r'permit\s+(.*?)\s+to\s+(?:access|reach)\s+(.*)',
            # "X must be able to access Y" / "X can access Y"
            r'(.*?)\s+(?:must be able to|can|should be able to)\s+access\s+(.*)',
            # "X must be reachable through Y"
            r'(.*?)\s+must\s+be\s+reachable\s+through\s+(.*)',
            # "enable traffic between X and Y"
            r'enable\s+(?:all\s+)?traffic\s+between\s+(.*?)\s+and\s+(.*)'
        ]

        for pat in allow_patterns:
            m = re.search(pat, nl)
            if m:
                if "reachable through" in pat:
                    dst = self._resolve_zone(m.group(1))
                    proto = m.group(2).strip()
                    src = "any"
                    return {
                        "status": "parsed",
                        "confidence": 0.88,
                        "policies": [{
                            "policy_type": "allow",
                            "action": "permit",
                            "source_zone": src,
                            "destination_zone": dst,
                            "protocol": proto,
                            "port": detected_port
                        }]
                    }
                else:
                    src = self._resolve_zone(m.group(1))
                    dst = self._resolve_zone(m.group(2))
                    return {
                        "status": "parsed",
                        "confidence": 0.90,
                        "policies": [{
                            "policy_type": "allow",
                            "action": "permit",
                            "source_zone": src,
                            "destination_zone": dst,
                            "protocol": detected_proto,
                            "port": detected_port
                        }]
                    }

        # Heuristic 1: Detect two known zones anywhere in text + sentiment
        found_zones = []
        for std_zone, syns in self.zone_synonyms.items():
            for s in syns:
                if re.search(r'\b' + re.escape(s) + r'\b', nl):
                    found_zones.append((std_zone, nl.find(s)))
                    break
        found_zones.sort(key=lambda x: x[1])

        # If IPs found, incorporate them
        if detected_ip_zones:
            for ipz in detected_ip_zones:
                found_zones.append((ipz, 0))

        if len(found_zones) >= 2:
            src = found_zones[0][0]
            dst = found_zones[1][0]
            is_deny = any(w in nl for w in ["block", "deny", "isolate", "prevent", "stop", "not", "cannot", "cant", "never", "no", "cut", "shut", "ban", "drop", "quarantine", "lockdown"])
            is_isolate = any(w in nl for w in ["isolate", "isolated", "isolation", "quarantine", "separate", "segregate"])
            return {
                "status": "parsed",
                "confidence": 0.88,
                "policies": [{
                    "policy_type": "isolate" if is_isolate else ("deny" if is_deny else "allow"),
                    "action": "deny" if is_deny else "permit",
                    "source_zone": src,
                    "destination_zone": dst,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        # Heuristic 2: Single Zone mentioned + security action
        # e.g., "quarantine guest", "secure the database", "block guest wifi", "isolate hr", "lockdown network"
        is_deny_action = any(w in nl for w in ["block", "deny", "isolate", "isolated", "prevent", "stop", "quarantine", "lockdown", "shut", "kill", "drop", "ban", "secure", "protect", "cut"])
        is_allow_action = any(w in nl for w in ["allow", "permit", "open", "connect", "enable", "access"])

        if len(found_zones) == 1:
            mentioned_zone = found_zones[0][0]
            if is_deny_action:
                # If guest, isolate from hr; if database/server, block guest from it
                if mentioned_zone == "guest":
                    src, dst = "guest", "hr"
                elif mentioned_zone in ["database", "hr", "backup", "application"]:
                    src, dst = "guest", mentioned_zone
                else:
                    src, dst = mentioned_zone, "guest"
                return {
                    "status": "parsed",
                    "confidence": 0.84,
                    "assumptions": f"Inferred protection target: block untrusted access between {src} and {dst}.",
                    "policies": [{
                        "policy_type": "isolate" if "isolate" in nl or "quarantine" in nl else "deny",
                        "action": "deny",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }
            elif is_allow_action:
                src, dst = mentioned_zone, "internet"
                return {
                    "status": "parsed",
                    "confidence": 0.82,
                    "assumptions": f"Inferred outbound reachability for {mentioned_zone} to internet.",
                    "policies": [{
                        "policy_type": "allow",
                        "action": "permit",
                        "source_zone": src,
                        "destination_zone": dst,
                        "protocol": detected_proto,
                        "port": detected_port
                    }]
                }

        # Heuristic 3: Check for general networking/security keywords without explicit zone
        # e.g., "disconnect clients", "block unauthorized devices", "enforce zero trust", "lockdown perimeter"
        has_network_terms = any(w in nl for w in [
            "traffic", "access", "network", "device", "devices", "server", "servers", "client", "clients", 
            "connection", "packet", "packets", "firewall", "switch", "router", "port", "zero trust", 
            "security", "policy", "rule", "lateral", "perimeter", "breach", "attack", "unauthorized"
        ])

        if (has_network_terms or fallback_on_unrecognized) and (is_deny_action or is_allow_action or fallback_on_unrecognized):
            # Universal zero-trust baseline inference
            p_type = "deny" if (is_deny_action or not is_allow_action) else "allow"
            act = "deny" if p_type == "deny" else "permit"
            src = "guest"
            dst = "hr" if p_type == "deny" else "internet"
            return {
                "status": "parsed",
                "confidence": 0.78,
                "assumptions": f"Zero-Trust Auto-Inference: Applied default perimeter security policy ({src} -> {dst}) for intent: '{natural_language}'.",
                "policies": [{
                    "policy_type": p_type,
                    "action": act,
                    "source_zone": src,
                    "destination_zone": dst,
                    "protocol": detected_proto,
                    "port": detected_port
                }]
            }

        return {"status": "draft", "confidence": 0.0, "policies": []}


