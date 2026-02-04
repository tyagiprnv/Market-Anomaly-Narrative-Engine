/**
 * API request/response types
 */

import { AnomalyDTO, NewsArticleDTO, NewsClusterDTO, UserDTO } from './database';
import { AnomalyType, ValidationStatus, NewsSentiment, NewsTiming } from './enums';

// Pagination
export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

// Authentication
export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  user: UserDTO;
  message: string;
}

// Anomaly queries
export interface AnomalyFilters {
  symbols?: string[];
  startDate?: string;
  endDate?: string;
  types?: AnomalyType[];
  validationStatus?: ValidationStatus[];
  page?: number;
  limit?: number;
}

export interface AnomalyStatsResponse {
  totalAnomalies: number;
  byType: Record<AnomalyType, number>;
  byValidation: Record<ValidationStatus, number>;
  bySymbol: Record<string, number>;
  averageConfidence: number;
}

export interface LatestAnomaliesRequest {
  since?: string; // ISO timestamp
  symbols?: string[];
}

// News queries
export interface NewsFilters {
  anomalyId?: string;
  symbols?: string[];
  sources?: string[];
  sentiment?: NewsSentiment[];
  timing?: NewsTiming[];
  startDate?: string;
  endDate?: string;
  page?: number;
  limit?: number;
}

export interface NewsClusterResponse {
  clusters: (NewsClusterDTO & { articles: NewsArticleDTO[] })[];
  unclustered: NewsArticleDTO[];
}

// Price queries
export interface PriceHistoryRequest {
  symbol: string;
  startDate: string;
  endDate: string;
  granularity?: '1m' | '5m' | '15m' | '1h';
}

export interface PriceHistoryResponse {
  symbol: string;
  granularity: string;
  data: Array<{
    timestamp: number;
    price: number;
    volume: number | null;
  }>;
}

// Symbol stats
export interface SymbolInfo {
  symbol: string;
  name: string;
  volatilityTier: string;
  threshold: number;
  recentAnomalyCount: number;
}

export interface SymbolStatsResponse {
  symbol: string;
  recentAnomalyCount24h: number;
  recentAnomalyCount7d: number;
  averageVolatility: number;
}

// Threshold config
export interface ThresholdConfig {
  volatility_tiers: Record<string, { multiplier: number }>;
  asset_specific_thresholds: Record<string, { z_score_threshold: number }>;
  multi_timeframe: {
    baseline_multiplier: number;
    windows_minutes: number[];
  };
}

// Error responses
export interface ErrorResponse {
  error: string;
  message: string;
  details?: unknown;
}
