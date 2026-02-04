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
        filters.symbols.forEach((s) => params.append('symbol', s));
      }
      if (filters.types?.length) {
        filters.types.forEach((t) => params.append('type', t));
      }
      if (filters.validationStatus?.length) {
        filters.validationStatus.forEach((v) => params.append('validationStatus', v));
      }
      if (filters.startDate) params.append('startDate', filters.startDate);
      if (filters.endDate) params.append('endDate', filters.endDate);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.limit) params.append('limit', filters.limit.toString());

      const response = await apiClient.get<PaginatedResponse<AnomalyDTO>>(
        `/anomalies?${params.toString()}`
      );
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
        request.symbols.forEach((s) => params.append('symbol', s));
      }

      const response = await apiClient.get<AnomalyDTO[]>(`/anomalies/latest?${params.toString()}`);
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
  options?: { enabled?: boolean }
): UseQueryResult<AnomalyStatsResponse> {
  return useQuery({
    queryKey: queryKeys.anomalies.stats(filters),
    queryFn: async () => {
      const params = new URLSearchParams();

      if (filters?.symbols?.length) {
        filters.symbols.forEach((s) => params.append('symbol', s));
      }
      if (filters?.types?.length) {
        filters.types.forEach((t) => params.append('type', t));
      }
      if (filters?.validationStatus?.length) {
        filters.validationStatus.forEach((v) => params.append('validationStatus', v));
      }
      if (filters?.startDate) params.append('startDate', filters.startDate);
      if (filters?.endDate) params.append('endDate', filters.endDate);

      const response = await apiClient.get<AnomalyStatsResponse>(
        `/anomalies/stats?${params.toString()}`
      );
      return response.data;
    },
    enabled: options?.enabled ?? true,
    staleTime: 60_000, // 1 minute
  });
}
