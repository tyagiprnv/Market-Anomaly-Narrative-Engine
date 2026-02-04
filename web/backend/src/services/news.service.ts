/**
 * News service - handles all news-related database operations
 */

import { Prisma } from '@prisma/client';
import prisma from '../config/database';
import { NewsArticleDTO, NewsClusterDTO, PaginatedResponse } from '@mane/shared';
import { toNewsArticleDTO, toNewsClusterDTO } from '../transformers/anomaly.transformer';
import { calculatePagination, calculateSkip } from '../utils/pagination';

export interface NewsFilters {
  symbol?: string;
  anomalyId?: string;
  startDate?: Date;
  endDate?: Date;
}

/**
 * Build Prisma where clause from filters
 */
function buildWhereClause(filters: NewsFilters): Prisma.news_articlesWhereInput {
  const where: Prisma.news_articlesWhereInput = {};

  // Anomaly ID filter
  if (filters.anomalyId) {
    where.anomaly_id = filters.anomalyId;
  }

  // Symbol filter (search in JSON field) - skip for now, complex with Prisma
  // Will filter in memory if needed or use raw SQL
  // TODO: Implement JSON array search if needed

  // Date range filter
  if (filters.startDate || filters.endDate) {
    where.published_at = {};
    if (filters.startDate) {
      where.published_at.gte = filters.startDate;
    }
    if (filters.endDate) {
      where.published_at.lte = filters.endDate;
    }
  }

  return where;
}

/**
 * Find all news articles with optional filters and pagination
 */
export async function findAll(
  filters: NewsFilters = {},
  page: number = 1,
  limit: number = 20
): Promise<PaginatedResponse<NewsArticleDTO>> {
  const where = buildWhereClause(filters);
  const skip = calculateSkip(page, limit);

  // Execute count and query in parallel
  const [total, articles] = await Promise.all([
    prisma.news_articles.count({ where }),
    prisma.news_articles.findMany({
      where,
      orderBy: { published_at: 'desc' },
      skip,
      take: limit,
    }),
  ]);

  const meta = calculatePagination(page, limit, total);

  return {
    data: articles.map(toNewsArticleDTO),
    meta,
  };
}

/**
 * Find news clusters for a specific anomaly with their articles
 */
export async function findClustersByAnomalyId(anomalyId: string): Promise<NewsClusterDTO[]> {
  // Get clusters for the anomaly
  const clusters = await prisma.news_clusters.findMany({
    where: { anomaly_id: anomalyId },
    orderBy: { cluster_number: 'asc' },
  });

  // Get all articles for this anomaly grouped by cluster
  const articles = await prisma.news_articles.findMany({
    where: { anomaly_id: anomalyId },
    orderBy: { published_at: 'desc' },
  });

  // Group articles by cluster_id
  const articlesByCluster = new Map<number, typeof articles>();
  articles.forEach((article) => {
    if (article.cluster_id !== null) {
      const existing = articlesByCluster.get(article.cluster_id) || [];
      existing.push(article);
      articlesByCluster.set(article.cluster_id, existing);
    }
  });

  // Transform clusters with their articles
  return clusters.map((cluster) => {
    const clusterArticles = cluster.cluster_number !== null
      ? articlesByCluster.get(cluster.cluster_number) || []
      : [];
    return toNewsClusterDTO(cluster, clusterArticles);
  });
}
