/**
 * Symbols Service
 * Provides information about supported symbols and their stats
 */

import {
  SUPPORTED_SYMBOLS,
  SYMBOL_NAMES,
  SupportedSymbol,
} from '@mane/shared/constants/symbols';
import { SYMBOL_VOLATILITY_TIERS } from '@mane/shared/constants/thresholds';
import { VolatilityTier } from '@mane/shared/types/enums';
import prisma from '../config/database';
import { thresholdsService } from './thresholds.service';
import logger from '../utils/logger';

/**
 * Symbol information with tier and threshold data
 */
export interface SymbolInfo {
  symbol: string;
  name: string;
  volatility_tier: VolatilityTier;
  tier_multiplier: number;
  z_score_threshold: number;
  volume_z_threshold: number;
  has_override: boolean;
}

/**
 * Symbol statistics from database
 */
export interface SymbolStats {
  symbol: string;
  name: string;
  volatility_tier: VolatilityTier;
  anomaly_count: number;
  narrative_count: number;
  latest_price: number | null;
  latest_price_time: Date | null;
  first_anomaly_time: Date | null;
  last_anomaly_time: Date | null;
  avg_anomaly_confidence: number | null;
}

class SymbolsService {
  /**
   * Get list of all supported symbols with tier and threshold info
   */
  async getAllSymbols(): Promise<SymbolInfo[]> {
    const thresholds = await thresholdsService.getAllAssetThresholds();

    // Create a map of symbol -> thresholds for efficient lookup
    const thresholdMap = new Map(thresholds.map((t) => [t.symbol, t]));

    // Map all supported symbols to SymbolInfo
    const symbols = SUPPORTED_SYMBOLS.map((symbol) => {
      const threshold = thresholdMap.get(symbol);
      const tier = SYMBOL_VOLATILITY_TIERS[symbol] || VolatilityTier.MODERATE;

      return {
        symbol,
        name: SYMBOL_NAMES[symbol],
        volatility_tier: tier,
        tier_multiplier: threshold?.tier_multiplier ?? 1.0,
        z_score_threshold: threshold?.z_score_threshold ?? 3.0,
        volume_z_threshold: threshold?.volume_z_threshold ?? 2.5,
        has_override: threshold?.is_override ?? false,
      };
    });

    return symbols;
  }

  /**
   * Get detailed statistics for a specific symbol
   */
  async getSymbolStats(symbol: string): Promise<SymbolStats | null> {
    try {
      // Validate symbol
      if (!SUPPORTED_SYMBOLS.includes(symbol as SupportedSymbol)) {
        return null;
      }

      const tier = SYMBOL_VOLATILITY_TIERS[symbol as SupportedSymbol] || VolatilityTier.MODERATE;

      // Get anomaly statistics
      const anomalyStats = await prisma.anomalies.aggregate({
        where: { symbol },
        _count: { id: true },
        _avg: { confidence: true },
      });

      const anomalyTimeRange = await prisma.anomalies.findFirst({
        where: { symbol },
        select: {
          detected_at: true,
        },
        orderBy: { detected_at: 'asc' },
      });

      const lastAnomaly = await prisma.anomalies.findFirst({
        where: { symbol },
        select: {
          detected_at: true,
        },
        orderBy: { detected_at: 'desc' },
      });

      // Get narrative count
      const narrativeCount = await prisma.narratives.count({
        where: {
          anomalies: {
            symbol,
          },
        },
      });

      // Get latest price
      const latestPrice = await prisma.prices.findFirst({
        where: { symbol },
        orderBy: { timestamp: 'desc' },
        select: {
          price: true,
          timestamp: true,
        },
      });

      return {
        symbol,
        name: SYMBOL_NAMES[symbol as SupportedSymbol],
        volatility_tier: tier,
        anomaly_count: anomalyStats._count.id,
        narrative_count: narrativeCount,
        latest_price: latestPrice ? Number(latestPrice.price) : null,
        latest_price_time: latestPrice?.timestamp || null,
        first_anomaly_time: anomalyTimeRange?.detected_at || null,
        last_anomaly_time: lastAnomaly?.detected_at || null,
        avg_anomaly_confidence: anomalyStats._avg.confidence
          ? Number(anomalyStats._avg.confidence)
          : null,
      };
    } catch (error) {
      logger.error(`Failed to get stats for symbol ${symbol}`, { error });
      throw error;
    }
  }

  /**
   * Get stats for all symbols
   */
  async getAllSymbolStats(): Promise<SymbolStats[]> {
    const statsPromises = SUPPORTED_SYMBOLS.map((symbol) => this.getSymbolStats(symbol));
    const results = await Promise.all(statsPromises);

    // Filter out nulls (shouldn't happen with valid symbols)
    return results.filter((s): s is SymbolStats => s !== null);
  }
}

// Export singleton instance
export const symbolsService = new SymbolsService();
