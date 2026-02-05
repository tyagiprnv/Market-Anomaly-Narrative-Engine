/**
 * React Query hooks for price API endpoints
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import apiClient from '../client';
import { queryKeys } from '../../utils/queryKeys';
import { PriceHistoryRequest, PriceHistoryResponse } from '@mane/shared/types/api';

/**
 * Fetch price history for a symbol with optional granularity
 */
export function usePriceHistory(
  request: PriceHistoryRequest,
  options?: { enabled?: boolean; refetchInterval?: number }
): UseQueryResult<PriceHistoryResponse> {
  return useQuery({
    queryKey: queryKeys.prices.history(
      request.symbol,
      request.startDate,
      request.endDate,
      request.granularity
    ),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('startDate', request.startDate);
      params.append('endDate', request.endDate);
      if (request.granularity) {
        params.append('granularity', request.granularity);
      }

      const response = await apiClient.get<PriceHistoryResponse>(
        `/prices/${request.symbol}?${params.toString()}`
      );
      return response.data;
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval, // Support polling for live updates
    staleTime: options?.refetchInterval ? 0 : 60_000, // If polling, always fetch fresh data
  });
}
