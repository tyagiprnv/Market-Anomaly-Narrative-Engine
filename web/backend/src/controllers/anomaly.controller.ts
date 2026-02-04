/**
 * Anomaly controller - handles HTTP requests for anomaly endpoints
 */

import { Request, Response, NextFunction } from 'express';
import * as anomalyService from '../services/anomaly.service';
import type {
  GetAnomaliesQuery,
  GetAnomalyByIdParams,
  GetLatestAnomaliesQuery,
  GetStatsQuery,
} from '../schemas/anomaly.schemas';
import logger from '../utils/logger';

/**
 * GET /api/anomalies
 * Get all anomalies with optional filters and pagination
 */
export async function getAnomalies(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { page, limit, symbol, symbols, anomalyType, validationStatus, startDate, endDate } =
      req.query as unknown as GetAnomaliesQuery;

    const filters = {
      symbol,
      symbols,
      anomalyType,
      validationStatus,
      startDate,
      endDate,
    };

    const result = await anomalyService.findAll(filters, page, limit);

    logger.info(
      `Retrieved ${result.data.length} anomalies (page ${page}/${result.meta.totalPages})`
    );

    res.json(result);
  } catch (error) {
    logger.error('Error fetching anomalies:', error);
    next(error);
  }
}

/**
 * GET /api/anomalies/:id
 * Get single anomaly by ID with all related data
 */
export async function getAnomalyById(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { id } = req.params as GetAnomalyByIdParams;

    const anomaly = await anomalyService.findById(id);

    if (!anomaly) {
      return res.status(404).json({
        error: 'NotFound',
        message: `Anomaly with ID ${id} not found`,
      });
    }

    logger.info(`Retrieved anomaly ${id}`);
    res.json(anomaly);
  } catch (error) {
    logger.error(`Error fetching anomaly ${req.params.id}:`, error);
    next(error);
  }
}

/**
 * GET /api/anomalies/latest
 * Get anomalies detected after a given timestamp (for polling)
 */
export async function getLatestAnomalies(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { since, symbols } = req.query as unknown as GetLatestAnomaliesQuery;

    const anomalies = await anomalyService.findLatest(since, symbols);

    logger.info(`Retrieved ${anomalies.length} anomalies since ${since.toISOString()}`);
    res.json(anomalies);
  } catch (error) {
    logger.error('Error fetching latest anomalies:', error);
    next(error);
  }
}

/**
 * GET /api/anomalies/stats
 * Get anomaly statistics
 */
export async function getAnomalyStats(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { symbols } = req.query as GetStatsQuery;

    const stats = await anomalyService.getStats(symbols);

    logger.info('Retrieved anomaly statistics');
    res.json(stats);
  } catch (error) {
    logger.error('Error fetching anomaly stats:', error);
    next(error);
  }
}
