/**
 * Shared enums matching the database schema
 */

export enum AnomalyType {
  PRICE_SPIKE = 'PRICE_SPIKE',
  PRICE_DROP = 'PRICE_DROP',
  VOLUME_SPIKE = 'VOLUME_SPIKE',
  COMBINED = 'COMBINED',
}

export enum ValidationStatus {
  VALID = 'VALID',
  INVALID = 'INVALID',
  PENDING = 'PENDING',
  NOT_GENERATED = 'NOT_GENERATED',
}

export enum NewsSentiment {
  POSITIVE = 'POSITIVE',
  NEGATIVE = 'NEGATIVE',
  NEUTRAL = 'NEUTRAL',
}

export enum NewsTiming {
  BEFORE = 'BEFORE',
  DURING = 'DURING',
  AFTER = 'AFTER',
}

export enum VolatilityTier {
  STABLE = 'stable',
  MODERATE = 'moderate',
  VOLATILE = 'volatile',
}
