import json
import yaml
import re

class ConfigParser:
    def parse(self, raw_content, fmt):
        if fmt.lower() == 'json':
            return self.parse_json(raw_content)
        elif fmt.lower() == 'yaml':
            return self.parse_yaml(raw_content)
        elif fmt.lower() in ['ios', 'cisco']:
            return self.parse_ios(raw_content)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def parse_json(self, content):
        try:
            parsed = json.loads(content)
            return self.normalize(parsed)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def parse_yaml(self, content):
        try:
            parsed = yaml.safe_load(content)
            return self.normalize(parsed)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {str(e)}")

    def parse_ios(self, content):
        result = {
            "hostname": "",
            "interfaces": [],
            "acls": [],
            "routes": [],
            "vlans": []
        }
        
        lines = content.split('\n')
        current_interface = None
        current_acl = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('!'):
                continue
                
            # Hostname
            host_match = re.match(r'^hostname\s+(\S+)', line)
            if host_match:
                result["hostname"] = host_match.group(1)
                
            # Interfaces
            intf_match = re.match(r'^interface\s+(\S+)', line)
            if intf_match:
                current_interface = {"name": intf_match.group(1), "ip_address": "", "subnet_mask": "", "status": "up", "vlan": None}
                result["interfaces"].append(current_interface)
                current_acl = None
                
            elif current_interface and line.startswith('ip address'):
                ip_match = re.match(r'^ip address\s+([\d\.]+)\s+([\d\.]+)', line)
                if ip_match:
                    current_interface["ip_address"] = ip_match.group(1)
                    current_interface["subnet_mask"] = ip_match.group(2)
                    
            elif current_interface and line == 'shutdown':
                current_interface["status"] = "down"
                
            # ACLs
            acl_match = re.match(r'^ip access-list extended\s+(\S+)', line)
            if acl_match:
                current_acl = {"name": acl_match.group(1), "rules": []}
                result["acls"].append(current_acl)
                current_interface = None
                
            elif current_acl and (line.startswith('permit') or line.startswith('deny')):
                parts = line.split()
                if len(parts) >= 4:
                    action = parts[0]
                    protocol = parts[1]
                    source = parts[2]
                    # basic simplified parsing
                    dest_idx = 4 if source != 'any' else 3
                    dest = parts[dest_idx] if len(parts) > dest_idx else 'any'
                    port = 'any'
                    if 'eq' in parts:
                        eq_idx = parts.index('eq')
                        if len(parts) > eq_idx + 1:
                            port = parts[eq_idx + 1]
                            
                    current_acl["rules"].append({
                        "action": action,
                        "protocol": protocol,
                        "source": source,
                        "destination": dest,
                        "port": port
                    })
                    
            # Routes
            route_match = re.match(r'^ip route\s+([\d\.]+)\s+([\d\.]+)\s+(\S+)', line)
            if route_match:
                result["routes"].append({
                    "network": route_match.group(1),
                    "mask": route_match.group(2),
                    "next_hop": route_match.group(3)
                })
                
        return result

    def normalize(self, parsed):
        # Ensure base structure
        normalized = {
            "hostname": parsed.get("hostname", ""),
            "interfaces": parsed.get("interfaces", []),
            "acls": parsed.get("acls", []),
            "routes": parsed.get("routes", []),
            "vlans": parsed.get("vlans", [])
        }
        return normalized

    def validate(self, content):
        errors = []
        if not content:
            errors.append({"line": 0, "error": "Empty configuration"})
        return errors
