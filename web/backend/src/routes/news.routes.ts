/**
 * News routes
 */

import { Router } from 'express';
import * as newsController from '../controllers/news.controller';
import { validateRequest } from '../middleware/validation';
import { authenticate } from '../middleware/auth';
import {
  getNewsQuerySchema,
  getNewsClustersByAnomalyIdParamsSchema,
} from '../schemas/news.schemas';

const router = Router();

// All news routes require authentication
router.use(authenticate);

/**
 * GET /api/news/clusters/:anomalyId
 * Must come before / to avoid route collision
 */
router.get(
  '/clusters/:anomalyId',
  validateRequest({ params: getNewsClustersByAnomalyIdParamsSchema }),
  newsController.getNewsClusters
);

/**
 * GET /api/news
 */
router.get('/', validateRequest({ query: getNewsQuerySchema }), newsController.getNews);

export default router;
