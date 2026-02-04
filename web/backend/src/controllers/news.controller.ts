/**
 * News controller - handles HTTP requests for news endpoints
 */

import { Request, Response, NextFunction } from 'express';
import * as newsService from '../services/news.service';
import type { GetNewsQuery, GetNewsClustersByAnomalyIdParams } from '../schemas/news.schemas';
import logger from '../utils/logger';

/**
 * GET /api/news
 * Get all news articles with optional filters and pagination
 */
export async function getNews(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { page, limit, symbol, anomalyId, startDate, endDate } = req.query as unknown as GetNewsQuery;

    const filters = {
      symbol,
      anomalyId,
      startDate,
      endDate,
    };

    const result = await newsService.findAll(filters, page, limit);

    logger.info(
      `Retrieved ${result.data.length} news articles (page ${page}/${result.meta.totalPages})`
    );

    res.json(result);
  } catch (error) {
    logger.error('Error fetching news articles:', error);
    next(error);
  }
}

/**
 * GET /api/news/clusters/:anomalyId
 * Get news clusters for a specific anomaly with their articles
 */
export async function getNewsClusters(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { anomalyId } = req.params as GetNewsClustersByAnomalyIdParams;

    const clusters = await newsService.findClustersByAnomalyId(anomalyId);

    logger.info(`Retrieved ${clusters.length} news clusters for anomaly ${anomalyId}`);
    res.json(clusters);
  } catch (error) {
    logger.error(`Error fetching news clusters for anomaly ${req.params.anomalyId}:`, error);
    next(error);
  }
}
