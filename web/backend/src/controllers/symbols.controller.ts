/**
 * Symbols Controller
 * Handles symbol-related API requests
 */

import { Request, Response, NextFunction } from 'express';
import { symbolsService } from '../services/symbols.service';
import logger from '../utils/logger';

/**
 * GET /api/symbols
 * Get list of all supported symbols with tier info
 */
export async function getAllSymbols(req: Request, res: Response, next: NextFunction) {
  try {
    const symbols = await symbolsService.getAllSymbols();

    res.json({
      success: true,
      data: symbols,
    });
  } catch (error) {
    logger.error('Failed to get symbols', { error });
    next(error);
  }
}

/**
 * GET /api/symbols/:symbol/stats
 * Get detailed statistics for a specific symbol
 */
export async function getSymbolStats(req: Request, res: Response, next: NextFunction) {
  try {
    const { symbol } = req.params;

    const stats = await symbolsService.getSymbolStats(symbol);

    if (!stats) {
      return res.status(404).json({
        success: false,
        error: 'Symbol not found',
      });
    }

    res.json({
      success: true,
      data: stats,
    });
  } catch (error) {
    logger.error('Failed to get symbol stats', { error, symbol: req.params.symbol });
    next(error);
  }
}

/**
 * GET /api/symbols/stats
 * Get statistics for all symbols
 */
export async function getAllSymbolStats(req: Request, res: Response, next: NextFunction) {
  try {
    const stats = await symbolsService.getAllSymbolStats();

    res.json({
      success: true,
      data: stats,
    });
  } catch (error) {
    logger.error('Failed to get all symbol stats', { error });
    next(error);
  }
}
