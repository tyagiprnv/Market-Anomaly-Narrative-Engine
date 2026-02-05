/**
 * Transforms Prisma models to API DTOs
 */

import type { anomalies, narratives, news_articles, news_clusters } from '@prisma/client';
import type {
  AnomalyDTO,
  NarrativeDTO,
  NewsArticleDTO,
  NewsClusterDTO,
  DetectionMetadata,
} from '@mane/shared';
import { AnomalyType, ValidationStatus, NewsSentiment, NewsTiming } from '@mane/shared';

type AnomalyWithRelations = anomalies & {
  narratives?: narratives | null;
  news_articles?: news_articles[];
  news_clusters?: news_clusters[];
};

/**
 * Map Prisma anomaly type enum to shared AnomalyType
 * Database stores values in lowercase, convert to uppercase enum
 */
function mapAnomalyType(type: string): AnomalyType {
  const upperType = type.toUpperCase();
  const mapping: Record<string, AnomalyType> = {
    PRICE_SPIKE: AnomalyType.PRICE_SPIKE,
    PRICE_DROP: AnomalyType.PRICE_DROP,
    VOLUME_SPIKE: AnomalyType.VOLUME_SPIKE,
    COMBINED: AnomalyType.COMBINED,
  };
  return mapping[upperType] || AnomalyType.COMBINED;
}

/**
 * Determine validation status from narrative data
 */
function getValidationStatus(narrative: narratives | null | undefined): ValidationStatus {
  if (!narrative) return ValidationStatus.NOT_GENERATED;
  if (!narrative.validated) return ValidationStatus.PENDING;
  return narrative.validation_passed ? ValidationStatus.VALID : ValidationStatus.INVALID;
}

/**
 * Map sentiment value to enum
 */
function mapSentiment(sentiment: number | null): NewsSentiment | null {
  if (sentiment === null) return null;
  if (sentiment > 0.1) return NewsSentiment.POSITIVE;
  if (sentiment < -0.1) return NewsSentiment.NEGATIVE;
  return NewsSentiment.NEUTRAL;
}

/**
 * Map timing tag to enum
 */
function mapTiming(timingTag: string | null): NewsTiming | null {
  if (!timingTag) return null;
  const mapping: Record<string, NewsTiming> = {
    before: NewsTiming.BEFORE,
    during: NewsTiming.DURING,
    after: NewsTiming.AFTER,
  };
  return mapping[timingTag] || null;
}

/**
 * Transform Prisma narrative to NarrativeDTO
 */
export function toNarrativeDTO(narrative: narratives): NarrativeDTO {
  return {
    id: narrative.id,
    anomalyId: narrative.anomaly_id || '',
    narrative: narrative.narrative_text,
    confidence: narrative.confidence_score || 0,
    validationStatus: getValidationStatus(narrative),
    validationReason: narrative.validation_reason,
    createdAt: narrative.created_at?.toISOString() || new Date().toISOString(),
  };
}

/**
 * Transform Prisma news article to NewsArticleDTO
 */
export function toNewsArticleDTO(article: news_articles): NewsArticleDTO {
  return {
    id: article.id,
    anomalyId: article.anomaly_id || '',
    title: article.title,
    url: article.url || '',
    source: article.source || 'unknown',
    publishedAt: article.published_at.toISOString(),
    sentiment: mapSentiment(article.sentiment),
    timing: mapTiming(article.timing_tag),
    clusterId: article.cluster_id?.toString() || null,
    createdAt: article.created_at?.toISOString() || new Date().toISOString(),
  };
}

/**
 * Transform Prisma news cluster to NewsClusterDTO
 */
export function toNewsClusterDTO(
  cluster: news_clusters,
  articles?: news_articles[]
): NewsClusterDTO {
  return {
    id: cluster.id,
    anomalyId: cluster.anomaly_id || '',
    clusterLabel: cluster.centroid_summary || `Cluster ${cluster.cluster_number}`,
    articleCount: cluster.size || 0,
    averageSentiment: mapSentiment(cluster.dominant_sentiment),
    createdAt: cluster.created_at?.toISOString() || new Date().toISOString(),
    articles: articles?.map(toNewsArticleDTO),
  };
}

/**
 * Transform Prisma anomaly to AnomalyDTO
 */
export function toAnomalyDTO(anomaly: AnomalyWithRelations): AnomalyDTO {
  return {
    id: anomaly.id,
    symbol: anomaly.symbol,
    detectedAt: anomaly.detected_at.toISOString(),
    anomalyType: mapAnomalyType(anomaly.anomaly_type),
    metrics: {
      zScore: anomaly.z_score,
      priceChangePct: anomaly.price_change_pct,
      volumeChangePct: anomaly.volume_change_pct,
      confidence: anomaly.confidence || 0,
    },
    priceSnapshot: {
      before: anomaly.price_before || 0,
      atDetection: anomaly.price_at_detection || 0,
      volumeBefore: anomaly.volume_before,
      volumeAtDetection: anomaly.volume_at_detection,
    },
    detectionMetadata: anomaly.detection_metadata as DetectionMetadata | null,
    baselineWindowMinutes: anomaly.baseline_window_minutes || 30,
    createdAt: anomaly.created_at?.toISOString() || new Date().toISOString(),
    // Optional nested relations
    narrative: anomaly.narratives ? toNarrativeDTO(anomaly.narratives) : undefined,
    newsArticles: anomaly.news_articles?.map(toNewsArticleDTO),
    newsClusters: anomaly.news_clusters?.map((c) => toNewsClusterDTO(c)),
  };
}
