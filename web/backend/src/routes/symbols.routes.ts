/**
 * Symbol Routes
 * /api/symbols/*
 */

import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { validateRequest } from '../middleware/validation';
import { symbolStatsParamsSchema } from '../schemas/config.schemas';
import * as symbolsController from '../controllers/symbols.controller';

const router = Router();

/**
 * GET /api/symbols
 * Get all supported symbols with tier info
 */
router.get('/', authenticate, symbolsController.getAllSymbols);

/**
 * GET /api/symbols/stats
 * Get statistics for all symbols
 * Note: Must be defined BEFORE /:symbol/stats to avoid route collision
 */
router.get('/stats', authenticate, symbolsController.getAllSymbolStats);

/**
 * GET /api/symbols/:symbol/stats
 * Get detailed statistics for a specific symbol
 */
router.get(
  '/:symbol/stats',
  authenticate,
  validateRequest({ params: symbolStatsParamsSchema }),
  symbolsController.getSymbolStats
);

export default router;
