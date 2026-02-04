/**
 * Thresholds Service
 * Parses and caches config/thresholds.yaml
 */

import fs from 'fs/promises';
import path from 'path';
import YAML from 'yaml';
import logger from '../utils/logger';

/**
 * Threshold configuration structure matching YAML file
 */
export interface ThresholdConfig {
  global_defaults: {
    z_score_threshold: number;
    volume_z_threshold: number;
    bollinger_std_multiplier: number;
  };
  volatility_tiers: {
    stable: VolatilityTierConfig;
    moderate: VolatilityTierConfig;
    volatile: VolatilityTierConfig;
  };
  asset_specific_thresholds: {
    [symbol: string]: {
      z_score_threshold?: number;
      volume_z_threshold?: number;
      description?: string;
    };
  };
  timeframes: {
    enabled: boolean;
    windows: number[];
    description: string;
    baseline_multiplier: number;
  };
  cumulative: {
    enabled: boolean;
    min_periods: number;
    description: string;
  };
}

export interface VolatilityTierConfig {
  description: string;
  multiplier: number;
  assets: string[];
}

export interface AssetThresholds {
  symbol: string;
  z_score_threshold: number;
  volume_z_threshold: number;
  volatility_tier: 'stable' | 'moderate' | 'volatile';
  tier_multiplier: number;
  is_override: boolean;
  description?: string;
}

class ThresholdsService {
  private config: ThresholdConfig | null = null;
  private configPath: string;

  constructor() {
    // Path to config/thresholds.yaml from project root
    this.configPath = path.join(__dirname, '../../../..', 'config', 'thresholds.yaml');
  }

  /**
   * Load and parse thresholds.yaml
   * Caches the result for subsequent calls
   */
  async loadConfig(): Promise<ThresholdConfig> {
    if (this.config) {
      return this.config;
    }

    try {
      logger.info(`Loading thresholds from: ${this.configPath}`);
      const fileContent = await fs.readFile(this.configPath, 'utf-8');
      this.config = YAML.parse(fileContent) as ThresholdConfig;
      logger.info('Thresholds configuration loaded successfully');
      return this.config;
    } catch (error) {
      logger.error('Failed to load thresholds.yaml', { error });
      throw new Error('Failed to load threshold configuration');
    }
  }

  /**
   * Get the full threshold configuration
   */
  async getConfig(): Promise<ThresholdConfig> {
    return this.loadConfig();
  }

  /**
   * Get thresholds for a specific asset
   */
  async getAssetThresholds(symbol: string): Promise<AssetThresholds> {
    const config = await this.loadConfig();

    // Check for asset-specific override first
    const override = config.asset_specific_thresholds[symbol];
    if (override) {
      const tier = this.getVolatilityTierForAsset(symbol, config);
      const tierConfig = config.volatility_tiers[tier];

      return {
        symbol,
        z_score_threshold: override.z_score_threshold ?? config.global_defaults.z_score_threshold,
        volume_z_threshold:
          override.volume_z_threshold ?? config.global_defaults.volume_z_threshold,
        volatility_tier: tier,
        tier_multiplier: tierConfig.multiplier,
        is_override: true,
        description: override.description,
      };
    }

    // Fall back to tier-based calculation
    const tier = this.getVolatilityTierForAsset(symbol, config);
    const tierConfig = config.volatility_tiers[tier];

    return {
      symbol,
      z_score_threshold: config.global_defaults.z_score_threshold * tierConfig.multiplier,
      volume_z_threshold: config.global_defaults.volume_z_threshold * tierConfig.multiplier,
      volatility_tier: tier,
      tier_multiplier: tierConfig.multiplier,
      is_override: false,
    };
  }

  /**
   * Get all asset thresholds
   */
  async getAllAssetThresholds(): Promise<AssetThresholds[]> {
    const config = await this.loadConfig();

    // Get all unique symbols from tier assignments
    const allSymbols = new Set<string>();
    Object.values(config.volatility_tiers).forEach((tier) => {
      tier.assets.forEach((asset) => allSymbols.add(asset));
    });

    // Also include any symbols with specific overrides
    Object.keys(config.asset_specific_thresholds).forEach((symbol) => {
      allSymbols.add(symbol);
    });

    // Get thresholds for each symbol
    const thresholds = await Promise.all(
      Array.from(allSymbols).map((symbol) => this.getAssetThresholds(symbol))
    );

    return thresholds.sort((a, b) => a.symbol.localeCompare(b.symbol));
  }

  /**
   * Determine which volatility tier a symbol belongs to
   */
  private getVolatilityTierForAsset(
    symbol: string,
    config: ThresholdConfig
  ): 'stable' | 'moderate' | 'volatile' {
    if (config.volatility_tiers.stable.assets.includes(symbol)) {
      return 'stable';
    }
    if (config.volatility_tiers.volatile.assets.includes(symbol)) {
      return 'volatile';
    }
    return 'moderate'; // Default to moderate
  }

  /**
   * Clear cached configuration (useful for testing or config reloads)
   */
  clearCache(): void {
    this.config = null;
  }
}

// Export singleton instance
export const thresholdsService = new ThresholdsService();
