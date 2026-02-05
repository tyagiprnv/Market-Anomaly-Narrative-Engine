/**
 * Price service - handles price data queries with auto-aggregation
 */

import { Prisma } from '@prisma/client';
import prisma from '../config/database';
import { PriceDataDTO } from '@mane/shared';
import { toPriceDataDTO } from '../transformers/price.transformer';

export interface PriceQueryOptions {
  symbol: string;
  startDate?: Date;
  endDate?: Date;
  aggregation?: 'auto' | '1m' | '5m' | '1h' | '1d';
}

/**
 * Aggregated price data result from database query
 */
interface AggregatedPrice {
  timestamp: Date;
  symbol: string;
  price: number;
  volume_24h: number | null;
}

/**
 * Determine aggregation interval based on date range
 */
function determineAggregation(startDate: Date, endDate: Date): string {
  const diffMs = endDate.getTime() - startDate.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffHours / 24;

  if (diffHours <= 24) {
    return '1m'; // Raw 1-minute data
  } else if (diffDays <= 7) {
    return '5m'; // 5-minute aggregation
  } else if (diffDays <= 30) {
    return '1h'; // 1-hour aggregation
  } else {
    return '1d'; // 1-day aggregation
  }
}

/**
 * Get time bucket truncation SQL based on aggregation level
 */
function getTimeBucketTruncation(aggregation: string): string {
  switch (aggregation) {
    case '1m':
      return "date_trunc('minute', timestamp)";
    case '5m':
      return "date_trunc('hour', timestamp) + interval '5 min' * floor(extract(minute from timestamp) / 5)";
    case '1h':
      return "date_trunc('hour', timestamp)";
    case '1d':
      return "date_trunc('day', timestamp)";
    default:
      return "date_trunc('minute', timestamp)";
  }
}

/**
 * Get price history for a symbol with auto-aggregation
 */
export async function getPriceHistory(options: PriceQueryOptions): Promise<{
  data: PriceDataDTO[];
  granularity: string;
}> {
  const { symbol, startDate, endDate, aggregation: requestedAggregation } = options;

  // Default to last 24 hours if no dates provided
  const end = endDate || new Date();
  const start = startDate || new Date(end.getTime() - 24 * 60 * 60 * 1000);

  // Determine aggregation level
  const aggregation = requestedAggregation === 'auto' || !requestedAggregation
    ? determineAggregation(start, end)
    : requestedAggregation;

  // If 1-minute data requested, use simple query (no aggregation)
  if (aggregation === '1m') {
    const prices = await prisma.prices.findMany({
      where: {
        symbol,
        timestamp: {
          gte: start,
          lte: end,
        },
      },
      orderBy: { timestamp: 'asc' },
    });

    return {
      data: prices.map(toPriceDataDTO),
      granularity: '1m',
    };
  }

  // Use raw SQL for aggregation
  const timeBucket = getTimeBucketTruncation(aggregation);

  const query = Prisma.sql`
    SELECT
      ${Prisma.raw(timeBucket)} as timestamp,
      symbol,
      AVG(price) as price,
      AVG(volume_24h) as volume_24h
    FROM prices
    WHERE symbol = ${symbol}
      AND timestamp >= ${start}
      AND timestamp <= ${end}
    GROUP BY ${Prisma.raw(timeBucket)}, symbol
    ORDER BY timestamp ASC
  `;

  const results = await prisma.$queryRaw<AggregatedPrice[]>(query);

  // Transform to DTO
  return {
    data: results.map((row) => ({
      timestamp: row.timestamp.toISOString(),
      symbol: row.symbol,
      price: row.price,
      volume: row.volume_24h,
    })),
    granularity: aggregation,
  };
}

/**
 * Get latest price for a symbol
 */
export async function getLatestPrice(symbol: string): Promise<PriceDataDTO | null> {
  const price = await prisma.prices.findFirst({
    where: { symbol },
    orderBy: { timestamp: 'desc' },
  });

  return price ? toPriceDataDTO(price) : null;
}
