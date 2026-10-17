import { apiClient } from './client';
import { Scenario, ScenarioResult } from '../types';

export const getScenarios = async (): Promise<Scenario[]> => {
  const response = await apiClient.get('/api/scenarios/');
  return response.data;
};

export const runScenario = async (scenarioId: string): Promise<ScenarioResult> => {
  const response = await apiClient.post(`/api/scenarios/${scenarioId}/run`);
  return response.data;
};

export const resetBaselineTopology = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post('/api/scenarios/reset/baseline');
  return response.data;
};
