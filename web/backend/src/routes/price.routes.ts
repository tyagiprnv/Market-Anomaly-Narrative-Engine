/**
 * Price routes
 */

import { Router } from 'express';
import * as priceController from '../controllers/price.controller';
import { validateRequest } from '../middleware/validation';
import { authenticate } from '../middleware/auth';
import {
  getPriceHistoryParamsSchema,
  getPriceHistoryQuerySchema,
} from '../schemas/price.schemas';

const router = Router();

// All price routes require authentication
router.use(authenticate);

/**
 * GET /api/prices/:symbol/latest
 * Must come before /:symbol to avoid route collision
 */
router.get(
  '/:symbol/latest',
  validateRequest({ params: getPriceHistoryParamsSchema }),
  priceController.getLatestPrice
);

/**
 * GET /api/prices/:symbol
 */
router.get(
  '/:symbol',
  validateRequest({
    params: getPriceHistoryParamsSchema,
    query: getPriceHistoryQuerySchema,
  }),
  priceController.getPriceHistory
);

export default router;
