/**
 * Config Routes
 * /api/config/*
 */

import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { validateRequest } from '../middleware/validation';
import { symbolStatsParamsSchema } from '../schemas/config.schemas';
import * as configController from '../controllers/config.controller';

const router = Router();

/**
 * GET /api/config/thresholds
 * Get the full threshold configuration
 */
router.get('/thresholds', authenticate, configController.getThresholds);

/**
 * GET /api/config/thresholds/:symbol
 * Get thresholds for a specific symbol
 */
router.get(
  '/thresholds/:symbol',
  authenticate,
  validateRequest({ params: symbolStatsParamsSchema }),
  configController.getAssetThresholds
);

export default router;
