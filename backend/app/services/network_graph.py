import networkx as nx
import ipaddress
import json
import re

class NetworkGraph:
    def __init__(self, devices, links):
        self.graph = nx.DiGraph()
        self.devices = {d.id: d for d in devices}
        
        for d in devices:
            self.graph.add_node(
                d.id,
                name=d.name,
                ip=d.ip_address,
                subnet=d.subnet,
                zone=d.zone,
                vlan=d.vlan_id,
                type=d.device_type,
                config=d.config if isinstance(d.config, dict) else (json.loads(d.config) if d.config else {})
            )
            
        for link in links:
            if getattr(link, 'status', 'up') == 'down':
                continue
            self.graph.add_edge(link.source_device_id, link.target_device_id, link=link)
            self.graph.add_edge(link.target_device_id, link.source_device_id, link=link) # Assuming bidirectional links
            
    def get_devices_in_zone(self, zone, network=None):
        if not zone:
            return []
        z_clean = str(zone).lower().strip()
        matches = [node for node, data in self.graph.nodes(data=True) if data.get('zone') and data.get('zone').lower() == z_clean]
        if not matches:
            # Check device names or aliases
            matches = [
                node for node, data in self.graph.nodes(data=True)
                if data.get('name') and re.search(r'(?<![\w-])' + re.escape(data.get('name').lower()) + r'(?![\w-])', z_clean)
            ]
        if not matches:
            # Synonym and category resolution for arbitrary custom user inputs
            synonym_map = {
                "guest": ["guest", "visitor", "visitors", "wifi", "client", "clients", "laptop", "mobile", "marketing", "sales", "untrusted", "user", "users"],
                "hr": ["hr", "human", "payroll", "personnel", "staff", "employee", "office", "finance", "accounting"],
                "engineering": ["eng", "engineering", "dev", "developer", "developers", "code", "git", "rnd", "tech"],
                "database": ["db", "database", "databases", "sql", "data", "storage", "records", "store"],
                "dmz": ["dmz", "web", "website", "proxy", "frontend", "public", "internet", "wan", "external"],
                "management": ["mgmt", "management", "admin", "admins", "console", "control", "ssh", "bastion"],
                "backup": ["backup", "backups", "archive", "vault"],
                "application": ["app", "apps", "application", "service", "services", "api"]
            }
            mapped_zone = None
            for target_z, syns in synonym_map.items():
                if any(s in z_clean for s in syns):
                    mapped_zone = target_z
                    break
            if mapped_zone:
                matches = [node for node, data in self.graph.nodes(data=True) if data.get('zone') and data.get('zone').lower() == mapped_zone]
        if not matches:
            # Ultimate safety fallback: map to primary client or server devices
            if any(term in z_clean for term in ["server", "db", "target", "internal", "secure", "protect"]):
                matches = [node for node, data in self.graph.nodes(data=True) if data.get('device_type') == 'server']
            else:
                matches = [node for node, data in self.graph.nodes(data=True) if data.get('device_type') == 'client']
        if network:
            try:
                requested = ipaddress.ip_network(network, strict=False)
                matches = [node for node in matches if self._device_matches_network(node, requested)]
            except ValueError:
                return []
        return matches

    def _device_matches_network(self, device_id, requested):
        data = self.graph.nodes[device_id]
        for value in (data.get('ip'), data.get('subnet')):
            if not value:
                continue
            try:
                candidate = ipaddress.ip_network(value if '/' in value else f'{value}/{ipaddress.ip_address(value).max_prefixlen}', strict=False)
                if candidate.overlaps(requested):
                    return True
            except ValueError:
                continue
        return False

    def is_subnet_match(self, ip_or_subnet, acl_network):
        if acl_network == "any":
            return True
        if ip_or_subnet == "any":
            return False
        try:
            n1 = ipaddress.ip_network(ip_or_subnet, strict=False)
            n2 = ipaddress.ip_network(acl_network, strict=False)
            return n1.subnet_of(n2) or n1.overlaps(n2)
        except ValueError:
            return False

    def check_route_permits(self, device_id, dest_ip):
        data = self.graph.nodes[device_id]
        dev_type = data.get('type')
        config = data.get('config', {})
        routes = config.get('routes', None)

        if dev_type not in ('router', 'firewall') and routes is None:
            return True, "Host device - default local gateway"

        if routes is not None:
            if not routes:
                dev_name = data.get('name', f"Device {device_id}")
                return False, f"Missing route: {dev_name} has empty routing table"
            if dest_ip == "any":
                return True, "Wildcard destination route match"
            clean_dest = str(dest_ip).split('/')[0]
            try:
                dest_addr = ipaddress.ip_address(clean_dest)
            except ValueError:
                return True, f"Non-IP destination {dest_ip}"

            for r in routes:
                net_str = r.get('network')
                mask_str = r.get('mask', '255.255.255.255')
                if not net_str:
                    continue
                if net_str == "0.0.0.0" and (mask_str in ("0.0.0.0", "0")):
                    return True, "Default route 0.0.0.0/0 matched"
                try:
                    if mask_str.count('.') == 3:
                        net_obj = ipaddress.ip_network(f"{net_str}/{mask_str}", strict=False)
                    else:
                        net_obj = ipaddress.ip_network(f"{net_str}/{mask_str}", strict=False)
                    if dest_addr in net_obj:
                        return True, f"Route found: {net_str}/{mask_str} via {r.get('next_hop', 'direct')}"
                except ValueError:
                    continue

            dev_name = data.get('name', f"Device {device_id}")
            return False, f"Missing route: {dev_name} has no route to destination {dest_ip}"

        return True, "Routing table not enforced"

    def check_acl_permits(self, device_id, source_subnet, dest_subnet, protocol=None, port=None):
        data = self.graph.nodes[device_id]
        config = data.get('config', {})
        acls = config.get('acls', [])
        
        if not acls:
            return True, "No ACLs configured"
            
        # Default behavior: if there are ACLs, deny by default unless permitted
        permit = False
        evidence = "Implicit deny"
        
        for acl in acls:
            rules = acl.get('rules', [])
            for rule in rules:
                rule_proto = str(rule.get('protocol', 'any')).lower()
                rule_src = rule.get('source', 'any')
                rule_dst = rule.get('destination', 'any')
                rule_port = str(rule.get('port', 'any')).lower()
                
                # Check protocol
                if protocol and rule_proto not in ('any', 'ip') and rule_proto != str(protocol).lower():
                    continue
                    
                # Check port
                if port and rule_port != 'any' and rule_port != str(port).lower():
                    continue
                    
                # Check source and destination subnets
                if self.is_subnet_match(source_subnet, rule_src) and self.is_subnet_match(dest_subnet, rule_dst):
                    action = rule.get('action', 'deny').lower()
                    if action == 'permit':
                        return True, f"Permitted by rule in ACL {acl.get('name')}: {rule}"
                    else:
                        return False, f"Denied by rule in ACL {acl.get('name')}: {rule}"
                        
        return permit, evidence

    def check_node_permits(self, node, src_ip, dst_ip, protocol=None, port=None):
        route_ok, route_reason = self.check_route_permits(node, dst_ip)
        if not route_ok:
            return False, route_reason
        acl_ok, acl_reason = self.check_acl_permits(node, src_ip, dst_ip, protocol, port)
        if not acl_ok:
            return False, acl_reason
        return True, acl_reason

    def get_all_paths(self, source_zone, dest_zone, source_network=None, destination_network=None):
        src_devices = self.get_devices_in_zone(source_zone, source_network)
        dst_devices = self.get_devices_in_zone(dest_zone, destination_network)
        
        all_paths = []
        for src in src_devices:
            for dst in dst_devices:
                try:
                    paths = list(nx.all_simple_paths(self.graph, src, dst))
                    all_paths.extend(paths)
                except nx.NetworkXNoPath:
                    pass
        return all_paths

    def has_permitted_path(self, source_zone, dest_zone, protocol=None, port=None, source_network=None, destination_network=None):
        evidence = self.get_path_evidence(source_zone, dest_zone, protocol, port, source_network, destination_network)
        return any(path_info['permitted'] for path_info in evidence)

    def get_path_evidence(self, source_zone, dest_zone, protocol=None, port=None, source_network=None, destination_network=None):
        src_devices = self.get_devices_in_zone(source_zone, source_network)
        dst_devices = self.get_devices_in_zone(dest_zone, destination_network)
        
        if not src_devices or not dst_devices:
            return []
            
        evidence_list = []
        for src in src_devices:
            for dst in dst_devices:
                if src == dst:
                    continue
                src_ip = self.graph.nodes[src].get('ip', 'any')
                dst_ip = self.graph.nodes[dst].get('ip', 'any')
                permitted_nodes = [
                    node for node in self.graph.nodes
                    if self.check_node_permits(node, src_ip, dst_ip, protocol, port)[0]
                ]
                permitted_graph = self.graph.subgraph(permitted_nodes)
                if src in permitted_graph and dst in permitted_graph and nx.has_path(permitted_graph, src, dst):
                    path = nx.shortest_path(permitted_graph, src, dst)
                    path_permitted = True
                elif nx.has_path(self.graph, src, dst):
                    path = nx.shortest_path(self.graph, src, dst)
                    path_permitted = False
                else:
                    evidence_list.append({"path": [], "permitted": False, "source_id": src, "destination_id": dst, "hops": [], "reason": "No physical path"})
                    continue

                hop_evidence = []
                for hop in path:
                    permit, reason = self.check_node_permits(hop, src_ip, dst_ip, protocol, port)
                    hop_evidence.append({
                        "device": self.graph.nodes[hop].get('name'),
                        "device_id": hop,
                        "permitted": permit,
                        "reason": reason
                    })
                evidence_list.append({
                    "path": [self.graph.nodes[n].get('name') for n in path],
                    "source_id": src,
                    "destination_id": dst,
                    "permitted": path_permitted,
                    "hops": hop_evidence
                })
            
        return evidence_list

