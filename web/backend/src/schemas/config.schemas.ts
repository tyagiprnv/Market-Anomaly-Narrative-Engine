/**
 * Validation schemas for config endpoints
 */

import { z } from 'zod';

/**
 * Schema for GET /api/symbols/:symbol/stats
 */
export const symbolStatsParamsSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
});
