/**
 * React Query hooks for anomaly API endpoints
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import apiClient from '../client';
import { queryKeys } from '../../utils/queryKeys';
import {
  AnomalyDTO,
  AnomalyFilters,
  AnomalyStatsResponse,
  LatestAnomaliesRequest,
  PaginatedResponse,
} from '@mane/shared/types/api';

/**
 * Fetch paginated anomalies with filters
 */
export function useAnomalies(
  filters: AnomalyFilters = {},
  options?: { enabled?: boolean }
): UseQueryResult<PaginatedResponse<AnomalyDTO>> {
  return useQuery({
    queryKey: queryKeys.anomalies.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();

      if (filters.symbols?.length) {
        // Send symbols as comma-separated string
        params.append('symbols', filters.symbols.join(','));
      }
      if (filters.types?.length) {
        // Send types as comma-separated string
        params.append('types', filters.types.join(','));
      }
      if (filters.validationStatus?.length) {
        // Send validation statuses as comma-separated string
        params.append('validationStatuses', filters.validationStatus.join(','));
      }
      if (filters.startDate) params.append('startDate', filters.startDate);
      if (filters.endDate) params.append('endDate', filters.endDate);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.limit) params.append('limit', filters.limit.toString());

      const queryString = params.toString();
      const url = queryString ? `/anomalies?${queryString}` : '/anomalies';
      const response = await apiClient.get<PaginatedResponse<AnomalyDTO>>(url);
      return response.data;
    },
    enabled: options?.enabled ?? true,
    staleTime: 30_000, // 30 seconds
  });
}

/**
 * Fetch latest anomalies with polling (for live updates)
 */
export function useLatestAnomalies(
  request: LatestAnomaliesRequest = {},
  options?: { enabled?: boolean; refetchInterval?: number }
): UseQueryResult<AnomalyDTO[]> {
  return useQuery({
    queryKey: queryKeys.anomalies.latest(request),
    queryFn: async () => {
      const params = new URLSearchParams();

      if (request.since) params.append('since', request.since);
      if (request.symbols?.length) {
        // Send symbols as comma-separated string
        params.append('symbols', request.symbols.join(','));
      }

      const queryString = params.toString();
      const url = queryString ? `/anomalies/latest?${queryString}` : '/anomalies/latest';
      const response = await apiClient.get<AnomalyDTO[]>(url);
      return response.data;
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval ?? 30_000, // 30 seconds by default
    staleTime: 0, // Always fetch fresh data
  });
}

/**
 * Fetch single anomaly by ID
 */
export function useAnomaly(
  id: string,
  options?: { enabled?: boolean }
): UseQueryResult<AnomalyDTO> {
  return useQuery({
    queryKey: queryKeys.anomalies.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<AnomalyDTO>(`/anomalies/${id}`);
      return response.data;
    },
    enabled: options?.enabled ?? true,
    staleTime: 60_000, // 1 minute
  });
}

/**
 * Fetch anomaly statistics
 */
export function useAnomalyStats(
  filters?: Omit<AnomalyFilters, 'page' | 'limit'>,
  options?: { enabled?: boolean; refetchInterval?: number }
): UseQueryResult<AnomalyStatsResponse> {
  return useQuery({
    queryKey: queryKeys.anomalies.stats(filters),
    queryFn: async () => {
      const params = new URLSearchParams();

      if (filters?.symbols?.length) {
        // Send symbols as comma-separated string
        params.append('symbols', filters.symbols.join(','));
      }
      if (filters?.types?.length) {
        filters.types.forEach((t) => params.append('type', t));
      }
      if (filters?.validationStatus?.length) {
        filters.validationStatus.forEach((v) => params.append('validationStatus', v));
      }
      if (filters?.startDate) params.append('startDate', filters.startDate);
      if (filters?.endDate) params.append('endDate', filters.endDate);

      const queryString = params.toString();
      const url = queryString ? `/anomalies/stats?${queryString}` : '/anomalies/stats';
      const response = await apiClient.get<AnomalyStatsResponse>(url);
      return response.data;
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval, // Support polling
    staleTime: options?.refetchInterval ? 0 : 60_000, // If polling, always fetch fresh data
  });
}
