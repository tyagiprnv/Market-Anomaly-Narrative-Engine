/**
 * Volatility tier mapping for symbols
 */

import { SupportedSymbol } from './symbols';
import { VolatilityTier } from '../types/enums';

export const SYMBOL_VOLATILITY_TIERS: Record<SupportedSymbol, VolatilityTier> = {
  // Stable (1.2x multiplier)
  'BTC-USD': VolatilityTier.STABLE,
  'ETH-USD': VolatilityTier.STABLE,

  // Moderate (1.0x multiplier)
  'SOL-USD': VolatilityTier.MODERATE,
  'XRP-USD': VolatilityTier.MODERATE,
  'ADA-USD': VolatilityTier.MODERATE,
  'AVAX-USD': VolatilityTier.MODERATE,
  'DOT-USD': VolatilityTier.MODERATE,
  'MATIC-USD': VolatilityTier.MODERATE,
  'LINK-USD': VolatilityTier.MODERATE,
  'UNI-USD': VolatilityTier.MODERATE,
  'LTC-USD': VolatilityTier.MODERATE,
  'ATOM-USD': VolatilityTier.MODERATE,
  'XLM-USD': VolatilityTier.MODERATE,
  'ALGO-USD': VolatilityTier.MODERATE,
  'VET-USD': VolatilityTier.MODERATE,
  'ICP-USD': VolatilityTier.MODERATE,
  'FIL-USD': VolatilityTier.MODERATE,
  'HBAR-USD': VolatilityTier.MODERATE,

  // Volatile (0.7x multiplier)
  'DOGE-USD': VolatilityTier.VOLATILE,
  'SHIB-USD': VolatilityTier.VOLATILE,
  'PEPE-USD': VolatilityTier.VOLATILE,
};

export const DEFAULT_THRESHOLDS = {
  z_score_threshold: 3.0,
  volume_threshold: 2.5,
  bollinger_std: 2.0,
};

export const TIER_MULTIPLIERS: Record<VolatilityTier, number> = {
  [VolatilityTier.STABLE]: 1.2,
  [VolatilityTier.MODERATE]: 1.0,
  [VolatilityTier.VOLATILE]: 0.7,
};
