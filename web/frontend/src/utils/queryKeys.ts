/**
 * React Query key factory for consistent cache keys
 */

import { AnomalyFilters, NewsFilters } from '@mane/shared/types/api';

export const queryKeys = {
  // Auth
  auth: {
    me: () => ['auth', 'me'] as const,
  },

  // Anomalies
  anomalies: {
    all: () => ['anomalies'] as const,
    list: (filters?: AnomalyFilters) => ['anomalies', 'list', filters] as const,
    detail: (id: string) => ['anomalies', 'detail', id] as const,
    latest: (request?: { since?: string; symbols?: string[] }) =>
      ['anomalies', 'latest', request] as const,
    stats: (filters?: Omit<AnomalyFilters, 'page' | 'limit'>) =>
      ['anomalies', 'stats', filters] as const,
  },

  // News
  news: {
    all: () => ['news'] as const,
    list: (filters?: NewsFilters) => ['news', 'list', filters] as const,
    clusters: (anomalyId: string) => ['news', 'clusters', anomalyId] as const,
  },

  // Prices
  prices: {
    history: (symbol: string, startDate: string, endDate: string, granularity?: string) =>
      ['prices', 'history', { symbol, startDate, endDate, granularity }] as const,
  },

  // Symbols
  symbols: {
    all: () => ['symbols'] as const,
    stats: (symbol: string) => ['symbols', 'stats', symbol] as const,
  },

  // Config
  config: {
    thresholds: () => ['config', 'thresholds'] as const,
  },
};
