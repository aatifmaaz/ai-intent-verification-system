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
        
        # Strip trailing punctuation
        nl = re.sub(r'[\.\!\?]+$', '', nl).strip()

        def clean_zone(text):
            if not text:
                return text
            t = text.strip()
            t = re.sub(r'^(the|all devices in the|all devices in|all)\s+', '', t).strip()
            t = re.sub(r'\s+(network|devices|zone|servers|server|clients|workstations)$', '', t).strip()
            return t or text.strip()

        if "must have internet access but must not access" in nl:
            match = re.search(r'(.*) must have internet access but must not access (.*)', nl)
            if match:
                s_zone = clean_zone(match.group(1))
                d_zone = clean_zone(match.group(2))
                return {
                    "status": "parsed",
                    "confidence": 0.9,
                    "policies": [
                        {"policy_type": "allow", "action": "permit", "source_zone": s_zone, "destination_zone": "internet", "protocol": "any", "port": "any"},
                        {"policy_type": "deny", "action": "deny", "source_zone": s_zone, "destination_zone": d_zone, "protocol": "any", "port": "any"}
                    ]
                }
                
        if "must remain isolated from" in nl:
            match = re.search(r'(.*) must remain isolated from (.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "isolate"
                action = "deny"
                confidence = 0.95
                
        elif "only" in nl and "may access" in nl:
            match = re.search(r'only (.*) may access (.*) using (.*)', nl)
            if match:
                src, dst, proto = clean_zone(match.group(1)), clean_zone(match.group(2)), match.group(3).strip()
                policy_type = "restrict"
                action = "permit"
                protocol = proto
                confidence = 0.9
                
        elif "must not communicate with" in nl:
            match = re.search(r'(.*) must not communicate with (.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "deny"
                action = "deny"
                confidence = 0.95

        elif "must not access" in nl or "cannot access" in nl or "should not access" in nl:
            match = re.search(r'(.*) (?:must not access|cannot access|should not access) (.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "deny"
                action = "deny"
                confidence = 0.92

        elif "isolate " in nl:
            match = re.search(r'isolate\s+(.*?)\s+from\s+(.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "isolate"
                action = "deny"
                confidence = 0.95

        elif "block " in nl:
            match = re.search(r'block\s+(.*?)\s+(?:from|to)\s+(.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "deny"
                action = "deny"
                confidence = 0.9

        elif "deny " in nl:
            match = re.search(r'deny\s+(.*?)\s+to\s+(.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "deny"
                action = "deny"
                confidence = 0.9
                
        elif "must be reachable through" in nl:
            match = re.search(r'(.*) must be reachable through (.*)', nl)
            if match:
                dst, proto = clean_zone(match.group(1)), match.group(2).strip()
                src = "any"
                policy_type = "allow"
                action = "permit"
                protocol = proto
                confidence = 0.85
                
        elif "must be able to access" in nl:
            match = re.search(r'(.*) must be able to access (.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
                policy_type = "allow"
                action = "permit"
                confidence = 0.9

        elif "allow " in nl:
            match = re.search(r'allow\s+(.*?)\s+to\s+(?:access\s+)?(.*)', nl)
            if match:
                src, dst = clean_zone(match.group(1)), clean_zone(match.group(2))
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

