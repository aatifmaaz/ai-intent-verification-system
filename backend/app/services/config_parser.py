import json
import yaml
import re
import ipaddress
from typing import Dict, Any, List, Optional

class ConfigParser:
    VALID_PROTOCOLS = {"ip", "tcp", "udp", "icmp", "any", "esp", "gre", "ospf"}
    VALID_ACTIONS = {"permit", "deny", "allow", "block"}

    def parse(self, raw_content: str, fmt: str = "json", format: Optional[str] = None) -> Dict[str, Any]:
        target_fmt = (format or fmt or "json").lower().strip()
        if not raw_content or not str(raw_content).strip():
            raise ValueError("Configuration content cannot be empty.")

        if target_fmt == 'json':
            return self.parse_json(raw_content)
        elif target_fmt == 'yaml':
            return self.parse_yaml(raw_content)
        elif target_fmt in ['ios', 'cisco']:
            return self.parse_ios(raw_content)
        else:
            raise ValueError(f"Unsupported format: {target_fmt}. Must be 'json', 'yaml', or 'ios'.")

    def _validate_ip_or_cidr(self, val: str, field_name: str = "IP address") -> None:
        if not val or val == "any":
            return
        clean_val = val.split('/')[0] if '/' in val else val
        try:
            ipaddress.ip_address(clean_val)
        except ValueError:
            raise ValueError(f"Invalid {field_name}: '{val}'")

    def _validate_port(self, port_val: Any) -> None:
        if port_val is None or str(port_val).lower() == "any":
            return
        port_str = str(port_val).strip()
        named_ports = {"ssh": 22, "http": 80, "https": 443, "dns": 53, "ntp": 123, "snmp": 161, "bgp": 179, "mysql": 3306, "postgres": 5432}
        if port_str.lower() in named_ports:
            return
        if '-' in port_str:
            parts = port_str.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                low, high = int(parts[0]), int(parts[1])
                if 1 <= low <= 65535 and 1 <= high <= 65535 and low <= high:
                    return
            raise ValueError(f"Invalid port range: '{port_val}'. Ports must be 1-65535.")
        if not port_str.isdigit() or not (1 <= int(port_str) <= 65535):
            raise ValueError(f"Invalid port number: '{port_val}'. Must be between 1 and 65535 or 'any'.")

    def _validate_normalized_structure(self, data: Dict[str, Any]) -> None:
        # Validate interfaces
        interfaces = data.get("interfaces", [])
        if not isinstance(interfaces, list):
            raise ValueError("'interfaces' must be a list of interface objects.")
        for intf in interfaces:
            if not isinstance(intf, dict):
                raise ValueError("Each interface entry must be an object.")
            if "ip_address" in intf and intf["ip_address"]:
                self._validate_ip_or_cidr(intf["ip_address"], "interface IP address")

        # Validate acls
        acls = data.get("acls", [])
        if not isinstance(acls, list):
            raise ValueError("'acls' must be a list of ACL objects.")
        for acl in acls:
            if not isinstance(acl, dict):
                raise ValueError("Each ACL entry must be an object.")
            rules = acl.get("rules", [])
            if not isinstance(rules, list):
                raise ValueError("ACL 'rules' must be a list.")
            for r in rules:
                if not isinstance(r, dict):
                    raise ValueError("Each rule in an ACL must be an object.")
                action = str(r.get("action", "")).lower()
                if action not in self.VALID_ACTIONS:
                    raise ValueError(f"Invalid ACL action: '{action}'. Must be 'permit' or 'deny'.")
                protocol = str(r.get("protocol", "ip")).lower()
                if protocol not in self.VALID_PROTOCOLS:
                    raise ValueError(f"Invalid protocol: '{protocol}'. Supported: {', '.join(sorted(self.VALID_PROTOCOLS))}")
                if "source" in r and r["source"] != "any":
                    self._validate_ip_or_cidr(r["source"], "source IP/CIDR")
                if "destination" in r and r["destination"] != "any":
                    self._validate_ip_or_cidr(r["destination"], "destination IP/CIDR")
                if "port" in r:
                    self._validate_port(r["port"])

        # Validate routes
        routes = data.get("routes", [])
        if not isinstance(routes, list):
            raise ValueError("'routes' must be a list of route objects.")
        for rt in routes:
            if not isinstance(rt, dict):
                raise ValueError("Each route entry must be an object.")
            if "network" in rt and rt["network"] != "0.0.0.0":
                self._validate_ip_or_cidr(rt["network"], "route destination network")
            if "next_hop" in rt and rt["next_hop"]:
                self._validate_ip_or_cidr(rt["next_hop"], "route next-hop IP")

    def parse_json(self, content: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}")
        if not isinstance(parsed, dict):
            raise ValueError("Invalid JSON configuration structure: top-level must be an object/dict, not a list or scalar.")
        normalized = self.normalize(parsed)
        self._validate_normalized_structure(normalized)
        return normalized

    def parse_yaml(self, content: str) -> Dict[str, Any]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            mark = getattr(e, 'problem_mark', None)
            loc = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            raise ValueError(f"Invalid YAML{loc}: {str(e)}")
        if not isinstance(parsed, dict):
            raise ValueError("Invalid YAML configuration structure: top-level must be a key-value mapping.")
        normalized = self.normalize(parsed)
        self._validate_normalized_structure(normalized)
        return normalized

    def parse_ios(self, content: str) -> Dict[str, Any]:
        result = {
            "hostname": "",
            "interfaces": [],
            "acls": [],
            "routes": [],
            "vlans": [],
            "unsupported_commands": []
        }
        
        lines = content.split('\n')
        current_interface = None
        current_acl = None
        numbered_acls: Dict[str, List[Dict[str, Any]]] = {}

        for line_no, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line or line.startswith('!'):
                continue
                
            # Hostname
            host_match = re.match(r'^hostname\s+(\S+)', line, re.IGNORECASE)
            if host_match:
                result["hostname"] = host_match.group(1)
                continue
                
            # Interfaces
            intf_match = re.match(r'^interface\s+(\S+)', line, re.IGNORECASE)
            if intf_match:
                current_interface = {"name": intf_match.group(1), "ip_address": "", "subnet_mask": "", "status": "up", "vlan": None}
                result["interfaces"].append(current_interface)
                current_acl = None
                continue
                
            if current_interface and line.lower().startswith('ip address'):
                ip_match = re.match(r'^ip address\s+([\d\.]+)\s+([\d\.]+)', line, re.IGNORECASE)
                if ip_match:
                    ip_str, mask_str = ip_match.group(1), ip_match.group(2)
                    self._validate_ip_or_cidr(ip_str, f"interface IP address (line {line_no})")
                    current_interface["ip_address"] = ip_str
                    current_interface["subnet_mask"] = mask_str
                continue
                    
            if current_interface and line.lower() == 'shutdown':
                current_interface["status"] = "down"
                continue
            if current_interface and line.lower() in ['no shutdown', 'no shut']:
                current_interface["status"] = "up"
                continue

            # Named Extended ACL: ip access-list extended <name>
            acl_match = re.match(r'^ip access-list extended\s+(\S+)', line, re.IGNORECASE)
            if acl_match:
                current_acl = {"name": acl_match.group(1), "rules": []}
                result["acls"].append(current_acl)
                current_interface = None
                continue
                
            # Named ACL rule
            if current_acl and (line.lower().startswith('permit') or line.lower().startswith('deny')):
                parts = line.split()
                if len(parts) >= 4:
                    action = parts[0].lower()
                    protocol = parts[1].lower()
                    source = parts[2]
                    dest_idx = 4 if source != 'any' else 3
                    dest = parts[dest_idx] if len(parts) > dest_idx else 'any'
                    port = 'any'
                    if 'eq' in parts:
                        eq_idx = parts.index('eq')
                        if len(parts) > eq_idx + 1:
                            port = parts[eq_idx + 1]
                    if source != "any":
                        self._validate_ip_or_cidr(source, f"ACL source IP (line {line_no})")
                    if dest != "any":
                        self._validate_ip_or_cidr(dest, f"ACL destination IP (line {line_no})")
                    self._validate_port(port)
                    current_acl["rules"].append({
                        "action": action,
                        "protocol": protocol,
                        "source": source,
                        "destination": dest,
                        "port": port
                    })
                continue

            # Standard/Extended Numbered ACL: access-list <num> permit/deny <proto> <src> <dst> [eq <port>]
            numbered_match = re.match(r'^access-list\s+(\d+)\s+(permit|deny)\s+(\S+)\s+(.*)', line, re.IGNORECASE)
            if numbered_match:
                acl_num = numbered_match.group(1)
                action = numbered_match.group(2).lower()
                protocol = numbered_match.group(3).lower()
                rest = numbered_match.group(4).split()
                source = rest[0] if len(rest) > 0 else 'any'
                dest = rest[1] if len(rest) > 1 and rest[1] != 'eq' else 'any'
                port = 'any'
                if 'eq' in rest:
                    eq_i = rest.index('eq')
                    if len(rest) > eq_i + 1:
                        port = rest[eq_i + 1]
                if source != "any":
                    self._validate_ip_or_cidr(source, f"numbered ACL source (line {line_no})")
                if dest != "any":
                    self._validate_ip_or_cidr(dest, f"numbered ACL dest (line {line_no})")
                self._validate_port(port)

                if acl_num not in numbered_acls:
                    numbered_acls[acl_num] = []
                numbered_acls[acl_num].append({
                    "action": action,
                    "protocol": protocol,
                    "source": source,
                    "destination": dest,
                    "port": port
                })
                continue
                    
            # Static Routes: ip route <network> <mask> <next_hop>
            route_match = re.match(r'^ip route\s+([\d\.]+)\s+([\d\.]+)\s+(\S+)', line, re.IGNORECASE)
            if route_match:
                net, mask, hop = route_match.group(1), route_match.group(2), route_match.group(3)
                if net != "0.0.0.0":
                    self._validate_ip_or_cidr(net, f"route network (line {line_no})")
                self._validate_ip_or_cidr(hop, f"route next-hop (line {line_no})")
                result["routes"].append({
                    "network": net,
                    "mask": mask,
                    "next_hop": hop
                })
                continue

            # VLANs: vlan <id>
            vlan_match = re.match(r'^vlan\s+(\d+)', line, re.IGNORECASE)
            if vlan_match:
                vlan_id = int(vlan_match.group(1))
                result["vlans"].append({"id": vlan_id, "name": f"VLAN_{vlan_id}"})
                continue

            # Unsupported or unrecognized command
            if not line.startswith('end') and not line.startswith('exit'):
                result["unsupported_commands"].append({"line_number": line_no, "command": line})

        # Append numbered ACLs to result
        for num, rules in numbered_acls.items():
            result["acls"].append({"name": f"ACL_{num}", "rules": rules})

        return self.normalize(result)

    def normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "hostname": parsed.get("hostname", ""),
            "interfaces": parsed.get("interfaces", []),
            "acls": parsed.get("acls", []),
            "routes": parsed.get("routes", []),
            "vlans": parsed.get("vlans", [])
        }
        if "unsupported_commands" in parsed:
            normalized["unsupported_commands"] = parsed["unsupported_commands"]
        return normalized

    def validate(self, content: str, format: str = "json") -> List[Dict[str, Any]]:
        errors = []
        if not content or not str(content).strip():
            return [{"line": 0, "error": "Empty configuration content"}]
        try:
            self.parse(content, format=format)
        except Exception as e:
            errors.append({"line": 1, "error": str(e)})
        return errors

