import { apiClient } from './client';
import { AuditEvent } from '../types';

export const getAuditLogs = async (
  limit = 100,
  eventType?: string,
  search?: string
): Promise<AuditEvent[]> => {
  const params: Record<string, string | number> = { limit };
  if (eventType && eventType !== 'ALL') {
    params.event_type = eventType;
  }
  if (search && search.trim() !== '') {
    params.search = search.trim();
  }
  const response = await apiClient.get('/api/audit-logs/', { params });
  return response.data;
};

export const getAuditEventTypes = async (): Promise<string[]> => {
  const response = await apiClient.get('/api/audit-logs/types');
  return response.data;
};
