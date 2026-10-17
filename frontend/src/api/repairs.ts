import { apiClient } from './client';
import { RepairProposal } from '../types';

export const getRepairs = async (status?: string): Promise<RepairProposal[]> => {
  const params = status && status !== 'all' ? { status } : {};
  const response = await apiClient.get('/api/repairs/', { params });
  return response.data;
};

export const getRepair = async (id: number): Promise<RepairProposal> => {
  const response = await apiClient.get(`/api/repairs/${id}`);
  return response.data;
};

export const proposeRepair = async (findingId: number): Promise<RepairProposal> => {
  const response = await apiClient.post('/api/repairs/propose', {
    finding_id: findingId,
  });
  return response.data;
};

export const validateRepair = async (
  repairId: number
): Promise<{ valid: boolean; status?: string; message: string; repair?: RepairProposal }> => {
  const response = await apiClient.post('/api/repairs/validate', {
    repair_id: repairId,
  });
  return response.data;
};

export const approveRepair = async (
  repairId: number
): Promise<{ message: string; repair?: RepairProposal }> => {
  const response = await apiClient.post(`/api/repairs/${repairId}/approve`);
  return response.data;
};

export const rollbackRepair = async (
  repairId: number
): Promise<{ message: string; repair?: RepairProposal }> => {
  const response = await apiClient.post(`/api/repairs/${repairId}/rollback`);
  return response.data;
};
