import networkx as nx
import ipaddress
import json

class NetworkGraph:
    def __init__(self, devices, links):
        self.graph = nx.DiGraph()
        self.devices = {d.id: d for d in devices}
        
        for d in devices:
            self.graph.add_node(
                d.id,
                name=d.name,
                ip=d.ip_address,
                zone=d.zone,
                vlan=d.vlan_id,
                type=d.device_type,
                config=d.config if isinstance(d.config, dict) else (json.loads(d.config) if d.config else {})
            )
            
        for link in links:
            self.graph.add_edge(link.source_device_id, link.target_device_id, link=link)
            self.graph.add_edge(link.target_device_id, link.source_device_id, link=link) # Assuming bidirectional links
            
    def get_devices_in_zone(self, zone):
        return [node for node, data in self.graph.nodes(data=True) if data.get('zone') == zone]

    def is_subnet_match(self, ip_or_subnet, acl_network):
        if acl_network == "any" or ip_or_subnet == "any":
            return True
        try:
            # Handle possible string formats
            n1 = ipaddress.ip_network(ip_or_subnet, strict=False)
            n2 = ipaddress.ip_network(acl_network, strict=False)
            return n1.overlaps(n2)
        except ValueError:
            return False

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

    def get_all_paths(self, source_zone, dest_zone):
        src_devices = self.get_devices_in_zone(source_zone)
        dst_devices = self.get_devices_in_zone(dest_zone)
        
        all_paths = []
        for src in src_devices:
            for dst in dst_devices:
                try:
                    paths = list(nx.all_simple_paths(self.graph, src, dst))
                    all_paths.extend(paths)
                except nx.NetworkXNoPath:
                    pass
        return all_paths

    def has_permitted_path(self, source_zone, dest_zone, protocol=None, port=None):
        evidence = self.get_path_evidence(source_zone, dest_zone, protocol, port)
        # Returns True if at least one fully permitted path exists
        return any(path_info['permitted'] for path_info in evidence)

    def get_path_evidence(self, source_zone, dest_zone, protocol=None, port=None):
        src_devices = self.get_devices_in_zone(source_zone)
        dst_devices = self.get_devices_in_zone(dest_zone)
        
        if not src_devices or not dst_devices:
            return []
            
        all_paths = self.get_all_paths(source_zone, dest_zone)
        evidence_list = []
        
        for path in all_paths:
            path_permitted = True
            hop_evidence = []
            
            src_ip = self.graph.nodes[path[0]].get('ip', 'any')
            dst_ip = self.graph.nodes[path[-1]].get('ip', 'any')
            
            for hop in path:
                permit, reason = self.check_acl_permits(hop, src_ip, dst_ip, protocol, port)
                hop_evidence.append({
                    "device": self.graph.nodes[hop].get('name'),
                    "device_id": hop,
                    "permitted": permit,
                    "reason": reason
                })
                if not permit:
                    path_permitted = False
                    
            evidence_list.append({
                "path": [self.graph.nodes[n].get('name') for n in path],
                "permitted": path_permitted,
                "hops": hop_evidence
            })
            
        return evidence_list
