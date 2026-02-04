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

// Symbol info and stats
export interface SymbolInfo {
  symbol: string;
  name: string;
  volatility_tier: string;
  tier_multiplier: number;
  z_score_threshold: number;
  volume_z_threshold: number;
  has_override: boolean;
}

export interface SymbolStats {
  symbol: string;
  name: string;
  volatility_tier: string;
  anomaly_count: number;
  narrative_count: number;
  latest_price: number | null;
  latest_price_time: string | null;
  first_anomaly_time: string | null;
  last_anomaly_time: string | null;
  avg_anomaly_confidence: number | null;
}

// Asset-specific thresholds
export interface AssetThresholds {
  symbol: string;
  z_score_threshold: number;
  volume_z_threshold: number;
  volatility_tier: 'stable' | 'moderate' | 'volatile';
  tier_multiplier: number;
  is_override: boolean;
  description?: string;
}

// Threshold config (matches thresholds.yaml structure)
export interface VolatilityTierConfig {
  description: string;
  multiplier: number;
  assets: string[];
}

export interface ThresholdConfig {
  global_defaults: {
    z_score_threshold: number;
    volume_z_threshold: number;
    bollinger_std_multiplier: number;
  };
  volatility_tiers: {
    stable: VolatilityTierConfig;
    moderate: VolatilityTierConfig;
    volatile: VolatilityTierConfig;
  };
  asset_specific_thresholds: {
    [symbol: string]: {
      z_score_threshold?: number;
      volume_z_threshold?: number;
      description?: string;
    };
  };
  timeframes: {
    enabled: boolean;
    windows: number[];
    description: string;
    baseline_multiplier: number;
  };
  cumulative: {
    enabled: boolean;
    min_periods: number;
    description: string;
  };
}

// Error responses
export interface ErrorResponse {
  error: string;
  message: string;
  details?: unknown;
}
