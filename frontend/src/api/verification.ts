import { apiClient } from './client';
import { VerificationRun } from '../types';

export const runVerification = async (): Promise<VerificationRun> => {
  const response = await apiClient.post('/api/verification/run');
  return response.data;
};

export const getVerificationResults = async (): Promise<VerificationRun[]> => {
  const response = await apiClient.get('/api/verification/results');
  return response.data;
};

export const getVerificationRun = async (runId: number): Promise<VerificationRun> => {
  const response = await apiClient.get(`/api/verification/results/${runId}`);
  return response.data;
};

export const getVerificationFindings = async (runId: number, status?: string) => {
  const params = status ? `?status=${status}` : '';
  const response = await apiClient.get(`/api/verification/results/${runId}/findings${params}`);
  return response.data;
};

export const proposeRepair = async (findingId: number) => {
  const response = await apiClient.post('/api/repairs/propose', { finding_id: findingId });
  return response.data;
};
