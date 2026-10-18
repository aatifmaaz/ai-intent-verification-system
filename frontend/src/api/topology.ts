import { apiClient } from './client';
import { TopologyData, Device, NetworkLink } from '../types';

export const getTopology = async (): Promise<TopologyData> => {
  const response = await apiClient.get('/api/topology/');
  return response.data;
};

export const createDevice = async (device: Partial<Device>): Promise<Device> => {
  const response = await apiClient.post('/api/topology/devices', device);
  return response.data;
};

export const updateDevice = async (id: number, device: Partial<Device>): Promise<Device> => {
  const response = await apiClient.put(`/api/topology/devices/${id}`, device);
  return response.data;
};

export const deleteDevice = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/topology/devices/${id}`);
};

export const createLink = async (link: Partial<NetworkLink>): Promise<NetworkLink> => {
  const response = await apiClient.post('/api/topology/links', link);
  return response.data;
};

export const deleteLink = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/topology/links/${id}`);
};

export interface TopologyTemplate {
  id: string;
  name: string;
  description: string;
  device_count: number;
  link_count: number;
  sample_intents: string[];
}

export const getTopologyTemplates = async (): Promise<TopologyTemplate[]> => {
  const response = await apiClient.get('/api/topology/templates');
  return response.data;
};

export const loadTopologyTemplate = async (templateId: string): Promise<{
  status: string;
  template: string;
  devices_count: number;
  links_count: number;
  message: string;
}> => {
  const response = await apiClient.post(`/api/topology/templates/${templateId}/load`);
  return response.data;
};

export const importCustomTopology = async (topologyData: {
  name?: string;
  devices: Array<Record<string, unknown>>;
  links: Array<Record<string, unknown>>;
  intents?: string[];
}): Promise<{
  status: string;
  name: string;
  devices_count: number;
  links_count: number;
  message: string;
}> => {
  const response = await apiClient.post('/api/topology/import', topologyData);
  return response.data;
};

