/**
 * Anomaly routes
 */

import { Router } from 'express';
import * as anomalyController from '../controllers/anomaly.controller';
import { validateRequest } from '../middleware/validation';
import { authenticate } from '../middleware/auth';
import {
  getAnomaliesQuerySchema,
  getAnomalyByIdParamsSchema,
  getLatestAnomaliesQuerySchema,
  getStatsQuerySchema,
} from '../schemas/anomaly.schemas';

const router = Router();

// All anomaly routes require authentication
router.use(authenticate);

/**
 * GET /api/anomalies/latest
 * Must come before /:id to avoid route collision
 */
router.get(
  '/latest',
  validateRequest({ query: getLatestAnomaliesQuerySchema }),
  anomalyController.getLatestAnomalies
);

/**
 * GET /api/anomalies/stats
 */
router.get(
  '/stats',
  validateRequest({ query: getStatsQuerySchema }),
  anomalyController.getAnomalyStats
);

/**
 * GET /api/anomalies
 */
router.get(
  '/',
  validateRequest({ query: getAnomaliesQuerySchema }),
  anomalyController.getAnomalies
);

/**
 * GET /api/anomalies/:id
 */
router.get(
  '/:id',
  validateRequest({ params: getAnomalyByIdParamsSchema }),
  anomalyController.getAnomalyById
);

export default router;
