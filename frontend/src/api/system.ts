import { apiClient } from './client';
import { SystemStatus } from '../types';

export const getSystemStatus = async (): Promise<SystemStatus> => {
  const response = await apiClient.get('/api/system/status');
  return response.data;
};

export const resetSystemTopology = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post('/api/scenarios/reset/baseline');
  return response.data;
};
