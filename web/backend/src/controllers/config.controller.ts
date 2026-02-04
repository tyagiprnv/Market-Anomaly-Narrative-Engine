/**
 * Config Controller
 * Handles configuration API requests
 */

import { Request, Response, NextFunction } from 'express';
import { thresholdsService } from '../services/thresholds.service';
import logger from '../utils/logger';

/**
 * GET /api/config/thresholds
 * Get the full threshold configuration
 */
export async function getThresholds(req: Request, res: Response, next: NextFunction) {
  try {
    const config = await thresholdsService.getConfig();

    res.json({
      success: true,
      data: config,
    });
  } catch (error) {
    logger.error('Failed to get thresholds config', { error });
    next(error);
  }
}

/**
 * GET /api/config/thresholds/:symbol
 * Get thresholds for a specific symbol
 */
export async function getAssetThresholds(req: Request, res: Response, next: NextFunction) {
  try {
    const { symbol } = req.params;

    const thresholds = await thresholdsService.getAssetThresholds(symbol);

    res.json({
      success: true,
      data: thresholds,
    });
  } catch (error) {
    logger.error('Failed to get asset thresholds', { error, symbol: req.params.symbol });
    next(error);
  }
}
