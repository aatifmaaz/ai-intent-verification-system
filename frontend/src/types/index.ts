// Types aligned with backend API response format

export interface Device {
  id: number;
  name: string;
  device_type: 'router' | 'switch' | 'firewall' | 'server' | 'client';
  ip_address: string;
  subnet: string;
  vlan_id: number | null;
  zone: string | null;
  interfaces: Record<string, unknown> | null;
  status: string;
  config: Record<string, unknown> | null;
}

export interface NetworkLink {
  id: number;
  source_device_id: number;
  target_device_id: number;
  source_interface: string | null;
  target_interface: string | null;
  link_type: string | null;
  bandwidth: string | null;
  status: string;
}

export interface TopologyData {
  devices: Device[];
  links: NetworkLink[];
}

export interface NormalizedPolicy {
  id: number;
  intent_id: number;
  policy_type: string;
  source_zone: string | null;
  source_network: string | null;
  destination_zone: string | null;
  destination_network: string | null;
  protocol: string | null;
  port: string | null;
  action: string;
  priority: number;
  conditions: Record<string, unknown> | null;
}

export interface Intent {
  id: number;
  natural_language: string;
  status: 'draft' | 'parsed' | 'active' | 'archived';
  confidence: number | null;
  assumptions: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  policies: NormalizedPolicy[];
}

export interface VerificationFinding {
  id: number;
  run_id: number;
  policy_id: number;
  status: 'PASS' | 'FAIL' | 'UNKNOWN';
  severity: string;
  risk_level: string | null;
  affected_devices: string[] | null;
  affected_networks: string[] | null;
  evidence: Record<string, unknown> | null;
  remediation: string | null;
  details: string | null;
}

export interface VerificationRun {
  id: number;
  started_at: string;
  completed_at: string | null;
  total_policies: number;
  passed: number;
  failed: number;
  unknown: number;
  status: string;
  findings: VerificationFinding[];
}

export interface RepairProposal {
  id: number;
  finding_id: number;
  policy_id: number;
  description: string;
  original_config: Record<string, unknown> | null;
  proposed_config: Record<string, unknown> | null;
  change_type: string;
  affected_devices: string[] | null;
  expected_result: string;
  validation_status: string;
  approval_status: string;
  approved_by: number | null;
  approved_at: string | null;
  applied_at: string | null;
  rolled_back_at: string | null;
}

export interface DashboardStats {
  total_devices: number;
  total_policies: number;
  passed: number;
  failed: number;
  unknown: number;
  pending_repairs: number;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  description: string;
  user_id: number | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  category: string;
  expected_result: string;
}

export interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  status: string;
  verification_results: VerificationFinding[];
  details: Record<string, unknown>;
}
