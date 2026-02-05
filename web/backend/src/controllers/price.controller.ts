/**
 * Price controller - handles HTTP requests for price endpoints
 */

import { Request, Response, NextFunction } from 'express';
import * as priceService from '../services/price.service';
import type { GetPriceHistoryParams, GetPriceHistoryQuery } from '../schemas/price.schemas';
import logger from '../utils/logger';

/**
 * GET /api/prices/:symbol
 * Get price history for a symbol with auto-aggregation
 */
export async function getPriceHistory(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { symbol } = req.params as GetPriceHistoryParams;
    const { startDate, endDate, aggregation } = req.query as unknown as GetPriceHistoryQuery;

    const result = await priceService.getPriceHistory({
      symbol,
      startDate,
      endDate,
      aggregation,
    });

    logger.info(
      `Retrieved ${result.data.length} price points for ${symbol} (${result.granularity} aggregation)`
    );

    // Return in PriceHistoryResponse format
    res.json({
      symbol,
      granularity: result.granularity,
      data: result.data.map((p) => ({
        timestamp: new Date(p.timestamp).getTime(), // Convert to Unix timestamp
        price: p.price,
        volume: p.volume,
      })),
    });
  } catch (error) {
    logger.error(`Error fetching price history for ${req.params.symbol}:`, error);
    next(error);
  }
}

/**
 * GET /api/prices/:symbol/latest
 * Get latest price for a symbol
 */
export async function getLatestPrice(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const { symbol } = req.params as GetPriceHistoryParams;

    const price = await priceService.getLatestPrice(symbol);

    if (!price) {
      return res.status(404).json({
        error: 'NotFound',
        message: `No price data found for symbol ${symbol}`,
      });
    }

    logger.info(`Retrieved latest price for ${symbol}`);
    res.json(price);
  } catch (error) {
    logger.error(`Error fetching latest price for ${req.params.symbol}:`, error);
    next(error);
  }
}
