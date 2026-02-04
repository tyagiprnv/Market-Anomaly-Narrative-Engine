/**
 * Zod validation schemas for news endpoints
 */

import { z } from 'zod';
import { uuidSchema } from './anomaly.schemas';

/**
 * Query parameters for GET /api/news
 */
export const getNewsQuerySchema = z.object({
  // Pagination
  page: z.coerce.number().int().min(1).optional().default(1),
  limit: z.coerce.number().int().min(1).max(100).optional().default(20),

  // Filters
  symbol: z.string().max(20).optional(),
  anomalyId: z.string().uuid('Invalid anomaly ID format').optional(),
  startDate: z.coerce.date().optional(),
  endDate: z.coerce.date().optional(),
});

export type GetNewsQuery = z.infer<typeof getNewsQuerySchema>;

/**
 * Route parameters for GET /api/news/clusters/:anomalyId
 */
export const getNewsClustersByAnomalyIdParamsSchema = z.object({
  anomalyId: uuidSchema,
});

export type GetNewsClustersByAnomalyIdParams = z.infer<
  typeof getNewsClustersByAnomalyIdParamsSchema
>;
