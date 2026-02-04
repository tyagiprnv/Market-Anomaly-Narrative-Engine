/**
 * Anomaly service - handles all anomaly-related database operations
 */

import { Prisma } from '@prisma/client';
import prisma from '../config/database';
import { AnomalyDTO, PaginatedResponse, ValidationStatus } from '@mane/shared';
import { toAnomalyDTO } from '../transformers/anomaly.transformer';
import { calculatePagination, calculateSkip } from '../utils/pagination';

export interface AnomalyFilters {
  symbol?: string;
  symbols?: string[];
  anomalyType?: string;
  validationStatus?: ValidationStatus;
  startDate?: Date;
  endDate?: Date;
}

export interface AnomalyStats {
  totalAnomalies: number;
  byType: Record<string, number>;
  byValidationStatus: Record<string, number>;
  recentCount24h: number;
  recentCount7d: number;
}

/**
 * Build Prisma where clause from filters
 */
function buildWhereClause(filters: AnomalyFilters): Prisma.anomaliesWhereInput {
  const where: Prisma.anomaliesWhereInput = {};

  // Symbol filter
  if (filters.symbol) {
    where.symbol = filters.symbol;
  } else if (filters.symbols && filters.symbols.length > 0) {
    where.symbol = { in: filters.symbols };
  }

  // Anomaly type filter
  if (filters.anomalyType) {
    where.anomaly_type = filters.anomalyType as any;
  }

  // Date range filter
  if (filters.startDate || filters.endDate) {
    where.detected_at = {};
    if (filters.startDate) {
      where.detected_at.gte = filters.startDate;
    }
    if (filters.endDate) {
      where.detected_at.lte = filters.endDate;
    }
  }

  // Validation status filter
  if (filters.validationStatus) {
    switch (filters.validationStatus) {
      case ValidationStatus.NOT_GENERATED:
        where.narratives = null;
        break;
      case ValidationStatus.PENDING:
        where.narratives = {
          validated: false,
        };
        break;
      case ValidationStatus.VALID:
        where.narratives = {
          validated: true,
          validation_passed: true,
        };
        break;
      case ValidationStatus.INVALID:
        where.narratives = {
          validated: true,
          validation_passed: false,
        };
        break;
    }
  }

  return where;
}

/**
 * Find all anomalies with optional filters and pagination
 */
export async function findAll(
  filters: AnomalyFilters = {},
  page: number = 1,
  limit: number = 20
): Promise<PaginatedResponse<AnomalyDTO>> {
  const where = buildWhereClause(filters);
  const skip = calculateSkip(page, limit);

  // Execute count and query in parallel
  const [total, anomalies] = await Promise.all([
    prisma.anomalies.count({ where }),
    prisma.anomalies.findMany({
      where,
      include: {
        narratives: true,
        news_articles: {
          take: 5, // Limit articles per anomaly in list view
          orderBy: { published_at: 'desc' },
        },
        news_clusters: true,
      },
      orderBy: { detected_at: 'desc' },
      skip,
      take: limit,
    }),
  ]);

  const meta = calculatePagination(page, limit, total);

  return {
    data: anomalies.map(toAnomalyDTO),
    meta,
  };
}

/**
 * Find anomaly by ID with all related data
 */
export async function findById(id: string): Promise<AnomalyDTO | null> {
  const anomaly = await prisma.anomalies.findUnique({
    where: { id },
    include: {
      narratives: true,
      news_articles: {
        orderBy: { published_at: 'desc' },
      },
      news_clusters: true,
    },
  });

  return anomaly ? toAnomalyDTO(anomaly) : null;
}

/**
 * Find latest anomalies for polling (efficient query)
 * Returns anomalies detected after the given timestamp
 */
export async function findLatest(
  since: Date,
  symbols?: string[]
): Promise<AnomalyDTO[]> {
  const where: Prisma.anomaliesWhereInput = {
    detected_at: { gt: since },
  };

  if (symbols && symbols.length > 0) {
    where.symbol = { in: symbols };
  }

  const anomalies = await prisma.anomalies.findMany({
    where,
    include: {
      narratives: true,
      news_articles: {
        take: 5,
        orderBy: { published_at: 'desc' },
      },
      news_clusters: true,
    },
    orderBy: { detected_at: 'desc' },
    take: 50, // Limit to prevent huge responses
  });

  return anomalies.map(toAnomalyDTO);
}

/**
 * Get anomaly statistics
 */
export async function getStats(
  symbols?: string[]
): Promise<AnomalyStats> {
  const where: Prisma.anomaliesWhereInput = {};
  if (symbols && symbols.length > 0) {
    where.symbol = { in: symbols };
  }

  const now = new Date();
  const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  // Execute all queries in parallel
  const [
    totalAnomalies,
    anomaliesByType,
    anomaliesWithNarrative,
    anomaliesWithValidNarrative,
    anomaliesWithInvalidNarrative,
    recent24h,
    recent7d,
  ] = await Promise.all([
    prisma.anomalies.count({ where }),
    prisma.anomalies.groupBy({
      by: ['anomaly_type'],
      where,
      _count: { anomaly_type: true },
    }),
    prisma.anomalies.count({
      where: {
        ...where,
        narratives: { isNot: null },
      },
    }),
    prisma.anomalies.count({
      where: {
        ...where,
        narratives: {
          validated: true,
          validation_passed: true,
        },
      },
    }),
    prisma.anomalies.count({
      where: {
        ...where,
        narratives: {
          validated: true,
          validation_passed: false,
        },
      },
    }),
    prisma.anomalies.count({
      where: {
        ...where,
        detected_at: { gte: twentyFourHoursAgo },
      },
    }),
    prisma.anomalies.count({
      where: {
        ...where,
        detected_at: { gte: sevenDaysAgo },
      },
    }),
  ]);

  // Build byType map
  const byType: Record<string, number> = {};
  anomaliesByType.forEach((group) => {
    byType[group.anomaly_type] = group._count.anomaly_type;
  });

  // Build validation status map
  const notGenerated = totalAnomalies - anomaliesWithNarrative;
  const pending = anomaliesWithNarrative - anomaliesWithValidNarrative - anomaliesWithInvalidNarrative;

  const byValidationStatus: Record<string, number> = {
    [ValidationStatus.NOT_GENERATED]: notGenerated,
    [ValidationStatus.PENDING]: pending,
    [ValidationStatus.VALID]: anomaliesWithValidNarrative,
    [ValidationStatus.INVALID]: anomaliesWithInvalidNarrative,
  };

  return {
    totalAnomalies,
    byType,
    byValidationStatus,
    recentCount24h: recent24h,
    recentCount7d: recent7d,
  };
}
