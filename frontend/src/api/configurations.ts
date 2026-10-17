import { apiClient } from './client';
import { NetworkConfiguration, DeviceConfigDetail } from '../types';

export const getConfigurations = async (): Promise<NetworkConfiguration[]> => {
  const response = await apiClient.get('/api/configurations/');
  return response.data;
};

export const getConfiguration = async (id: number): Promise<NetworkConfiguration> => {
  const response = await apiClient.get(`/api/configurations/${id}`);
  return response.data;
};

export const getDeviceConfigurations = async (deviceId: number): Promise<DeviceConfigDetail> => {
  const response = await apiClient.get(`/api/configurations/device/${deviceId}`);
  return response.data;
};

export const importConfiguration = async (
  deviceId: number,
  format: 'json' | 'yaml' | 'ios',
  content: string
): Promise<NetworkConfiguration> => {
  const response = await apiClient.post('/api/configurations/import', {
    device_id: deviceId,
    format,
    content,
  });
  return response.data;
};

export const validateConfiguration = async (
  format: 'json' | 'yaml' | 'ios',
  content: string
): Promise<{ valid: boolean; format: string; parsed?: Record<string, unknown>; error?: string; message: string }> => {
  const response = await apiClient.post('/api/configurations/validate', {
    format,
    content,
  });
  return response.data;
};
