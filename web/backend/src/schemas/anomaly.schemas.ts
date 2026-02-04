/**
 * Zod validation schemas for anomaly endpoints
 */

import { z } from 'zod';
import { AnomalyType, ValidationStatus } from '@mane/shared';

/**
 * UUID v4 validation
 */
export const uuidSchema = z.string().uuid('Invalid anomaly ID format');

/**
 * Query parameters for GET /api/anomalies
 */
export const getAnomaliesQuerySchema = z.object({
  // Pagination
  page: z.coerce.number().int().min(1).optional().default(1),
  limit: z.coerce.number().int().min(1).max(100).optional().default(20),

  // Filters
  symbol: z.string().max(20).optional(),
  symbols: z
    .string()
    .optional()
    .transform((val) => (val ? val.split(',').map((s) => s.trim()) : undefined)),
  anomalyType: z.nativeEnum(AnomalyType).optional(),
  validationStatus: z.nativeEnum(ValidationStatus).optional(),
  startDate: z.coerce.date().optional(),
  endDate: z.coerce.date().optional(),
});

export type GetAnomaliesQuery = z.infer<typeof getAnomaliesQuerySchema>;

/**
 * Route parameters for GET /api/anomalies/:id
 */
export const getAnomalyByIdParamsSchema = z.object({
  id: uuidSchema,
});

export type GetAnomalyByIdParams = z.infer<typeof getAnomalyByIdParamsSchema>;

/**
 * Query parameters for GET /api/anomalies/latest
 */
export const getLatestAnomaliesQuerySchema = z.object({
  since: z.coerce.date(),
  symbols: z
    .string()
    .optional()
    .transform((val) => (val ? val.split(',').map((s) => s.trim()) : undefined)),
});

export type GetLatestAnomaliesQuery = z.infer<typeof getLatestAnomaliesQuerySchema>;

/**
 * Query parameters for GET /api/anomalies/stats
 */
export const getStatsQuerySchema = z.object({
  symbols: z
    .string()
    .optional()
    .transform((val) => (val ? val.split(',').map((s) => s.trim()) : undefined)),
});

export type GetStatsQuery = z.infer<typeof getStatsQuerySchema>;
