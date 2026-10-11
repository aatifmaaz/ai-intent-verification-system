import { apiClient } from './client';
import { DashboardStats, AuditEvent } from '../types';

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const response = await apiClient.get('/api/dashboard/stats');
  return response.data;
};

export const getRecentActivity = async (limit: number = 10): Promise<AuditEvent[]> => {
  const response = await apiClient.get(`/api/audit-logs/?limit=${limit}`);
  return response.data;
};

export const getVerificationHistory = async (): Promise<{ runs: Array<{ id: number; started_at: string; passed: number; failed: number; unknown: number }> }> => {
  const response = await apiClient.get('/api/verification/results');
  return { runs: response.data };
};
