/**
 * DTOs matching the database schema
 */

import { AnomalyType, ValidationStatus, NewsSentiment, NewsTiming } from './enums';

export interface DetectionMetadata {
  timeframe_minutes?: number;
  volatility_tier?: string;
  asset_threshold?: number;
  threshold_source?: string;
  detector?: string;
}

export interface AnomalyMetrics {
  zScore: number | null;
  priceChangePct: number | null;
  volumeChangePct: number | null;
  confidence: number;
}

export interface PriceSnapshot {
  before: number;
  atDetection: number;
  volumeBefore: number | null;
  volumeAtDetection: number | null;
}

export interface AnomalyDTO {
  id: string;
  symbol: string;
  detectedAt: string;
  anomalyType: AnomalyType;
  metrics: AnomalyMetrics;
  priceSnapshot: PriceSnapshot;
  detectionMetadata: DetectionMetadata | null;
  baselineWindowMinutes: number;
  createdAt: string;
  // Optional nested relations
  narrative?: NarrativeDTO;
  newsArticles?: NewsArticleDTO[];
  newsClusters?: NewsClusterDTO[];
}

export interface NewsArticleDTO {
  id: string;
  anomalyId: string;
  title: string;
  url: string;
  source: string;
  publishedAt: string;
  sentiment: NewsSentiment | null;
  timing: NewsTiming | null;
  clusterId: string | null;
  createdAt: string;
}

export interface NewsClusterDTO {
  id: string;
  anomalyId: string;
  clusterLabel: string;
  articleCount: number;
  averageSentiment: NewsSentiment | null;
  createdAt: string;
  // Optional nested relations
  articles?: NewsArticleDTO[];
}

export interface NarrativeDTO {
  id: string;
  anomalyId: string;
  narrative: string;
  confidence: number;
  validationStatus: ValidationStatus;
  validationReason: string | null;
  createdAt: string;
}

export interface PriceDataDTO {
  timestamp: string;
  symbol: string;
  price: number;
  volume: number | null;
}

export interface UserDTO {
  id: string;
  email: string;
  createdAt: string;
  updatedAt: string;
}
