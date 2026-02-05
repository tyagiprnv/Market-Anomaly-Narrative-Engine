/**
 * Zod validation schemas for price endpoints
 */

import { z } from 'zod';

/**
 * Route parameters for GET /api/prices/:symbol
 */
export const getPriceHistoryParamsSchema = z.object({
  symbol: z.string().max(20).toUpperCase(),
});

export type GetPriceHistoryParams = z.infer<typeof getPriceHistoryParamsSchema>;

/**
 * Query parameters for GET /api/prices/:symbol
 */
export const getPriceHistoryQuerySchema = z.object({
  startDate: z.coerce.date().optional(),
  endDate: z.coerce.date().optional(),
  // Accept both 'granularity' and 'aggregation' for backwards compatibility
  granularity: z.enum(['auto', '1m', '5m', '15m', '1h', '1d']).optional(),
  aggregation: z.enum(['auto', '1m', '5m', '15m', '1h', '1d']).optional(),
}).transform((data) => ({
  startDate: data.startDate,
  endDate: data.endDate,
  // Use granularity if provided, otherwise aggregation, otherwise default to 'auto'
  aggregation: data.granularity || data.aggregation || 'auto',
}));

export type GetPriceHistoryQuery = z.infer<typeof getPriceHistoryQuerySchema>;
