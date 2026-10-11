import { apiClient } from './client';
import { Intent } from '../types';

export const getIntents = async (): Promise<Intent[]> => {
  const response = await apiClient.get('/api/intents/');
  return response.data;
};

export const createIntent = async (naturalLanguage: string): Promise<Intent> => {
  const response = await apiClient.post('/api/intents/', {
    natural_language: naturalLanguage,
  });
  return response.data;
};

export const getIntent = async (id: number): Promise<Intent> => {
  const response = await apiClient.get(`/api/intents/${id}`);
  return response.data;
};

export const updateIntent = async (id: number, naturalLanguage: string): Promise<Intent> => {
  const response = await apiClient.put(`/api/intents/${id}`, {
    natural_language: naturalLanguage,
  });
  return response.data;
};

export const deleteIntent = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/intents/${id}`);
};
