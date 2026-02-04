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
  aggregation: z.enum(['auto', '1m', '5m', '1h', '1d']).optional().default('auto'),
});

export type GetPriceHistoryQuery = z.infer<typeof getPriceHistoryQuerySchema>;
