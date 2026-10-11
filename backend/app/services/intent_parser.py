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
                
        if "must remain isolated from" in nl:
            match = re.search(r'(.*) must remain isolated from (.*)', nl)
            if match:
                src, dst = match.group(1).strip(), match.group(2).strip()
                policy_type = "isolate"
                action = "deny"
                confidence = 0.95
                
        elif "only" in nl and "may access" in nl:
            match = re.search(r'only (.*) may access (.*) using (.*)', nl)
            if match:
                src, dst, proto = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
                policy_type = "restrict"
                action = "permit"
                protocol = proto
                confidence = 0.9
                
        elif "must not communicate with" in nl:
            match = re.search(r'(.*) must not communicate with (.*)', nl)
            if match:
                src, dst = match.group(1).strip(), match.group(2).strip()
                policy_type = "deny"
                action = "deny"
                confidence = 0.95
                
        elif "must be reachable through" in nl:
            match = re.search(r'(.*) must be reachable through (.*)', nl)
            if match:
                dst, proto = match.group(1).strip(), match.group(2).strip()
                src = "any"
                policy_type = "allow"
                action = "permit"
                protocol = proto
                confidence = 0.85
                
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
