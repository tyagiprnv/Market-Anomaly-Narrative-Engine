# Phase 5: Config & Symbols API - Implementation Summary

## Overview

Phase 5 adds configuration and symbol information endpoints to the API, enabling the frontend to:
1. Query supported symbols with their volatility tiers and thresholds
2. Get statistics for symbols (anomaly counts, price data, etc.)
3. Access the threshold configuration from `config/thresholds.yaml`
4. Retrieve asset-specific threshold overrides

## New Endpoints

### Symbol Endpoints

#### 1. GET /api/symbols
Get list of all supported symbols with tier and threshold information.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "BTC-USD",
      "name": "Bitcoin",
      "volatility_tier": "stable",
      "tier_multiplier": 1.2,
      "z_score_threshold": 3.5,
      "volume_z_threshold": 2.8,
      "has_override": true
    },
    {
      "symbol": "DOGE-USD",
      "name": "Dogecoin",
      "volatility_tier": "volatile",
      "tier_multiplier": 0.7,
      "z_score_threshold": 2.0,
      "volume_z_threshold": 2.0,
      "has_override": true
    }
    // ... 19 more symbols (21 total)
  ]
}
```

#### 2. GET /api/symbols/:symbol/stats
Get detailed statistics for a specific symbol.

**Example:** `GET /api/symbols/BTC-USD/stats`

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTC-USD",
    "name": "Bitcoin",
    "volatility_tier": "stable",
    "anomaly_count": 1,
    "narrative_count": 1,
    "latest_price": 95300,
    "latest_price_time": "2026-02-04T18:27:04.256Z",
    "first_anomaly_time": "2026-02-04T18:27:04.256Z",
    "last_anomaly_time": "2026-02-04T18:27:04.256Z",
    "avg_anomaly_confidence": 0.5597118414360708
  }
}
```

#### 3. GET /api/symbols/stats
Get statistics for all supported symbols.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "BTC-USD",
      "name": "Bitcoin",
      "volatility_tier": "stable",
      "anomaly_count": 1,
      "narrative_count": 1,
      "latest_price": 95300,
      "latest_price_time": "2026-02-04T18:27:04.256Z",
      "first_anomaly_time": "2026-02-04T18:27:04.256Z",
      "last_anomaly_time": "2026-02-04T18:27:04.256Z",
      "avg_anomaly_confidence": 0.56
    }
    // ... stats for all 21 symbols
  ]
}
```

### Config Endpoints

#### 4. GET /api/config/thresholds
Get the complete threshold configuration from `config/thresholds.yaml`.

**Response:**
```json
{
  "success": true,
  "data": {
    "global_defaults": {
      "z_score_threshold": 3.0,
      "volume_z_threshold": 2.5,
      "bollinger_std_multiplier": 2.0
    },
    "volatility_tiers": {
      "stable": {
        "description": "Major cryptocurrencies with lower volatility",
        "multiplier": 1.2,
        "assets": ["BTC-USD", "ETH-USD"]
      },
      "moderate": {
        "description": "Major altcoins with medium volatility",
        "multiplier": 1.0,
        "assets": ["SOL-USD", "XRP-USD", ...]
      },
      "volatile": {
        "description": "Meme coins and highly volatile assets",
        "multiplier": 0.7,
        "assets": ["DOGE-USD", "SHIB-USD", "PEPE-USD"]
      }
    },
    "asset_specific_thresholds": {
      "BTC-USD": {
        "z_score_threshold": 3.5,
        "volume_z_threshold": 2.8,
        "description": "Bitcoin: Most stable, requires higher threshold"
      },
      "DOGE-USD": {
        "z_score_threshold": 2.0,
        "volume_z_threshold": 2.0,
        "description": "Dogecoin: Highly volatile meme coin"
      }
    },
    "timeframes": {
      "enabled": true,
      "windows": [5, 15, 30, 60],
      "description": "Detect anomalies across multiple timeframes",
      "baseline_multiplier": 3
    },
    "cumulative": {
      "enabled": true,
      "min_periods": 3,
      "description": "Detect slow burns (cumulative price changes over time)"
    }
  }
}
```

#### 5. GET /api/config/thresholds/:symbol
Get threshold configuration for a specific symbol.

**Example:** `GET /api/config/thresholds/BTC-USD`

**Response (with override):**
```json
{
  "success": true,
  "data": {
    "symbol": "BTC-USD",
    "z_score_threshold": 3.5,
    "volume_z_threshold": 2.8,
    "volatility_tier": "stable",
    "tier_multiplier": 1.2,
    "is_override": true,
    "description": "Bitcoin: Most stable, requires higher threshold"
  }
}
```

**Response (no override):**
```json
{
  "success": true,
  "data": {
    "symbol": "SOL-USD",
    "z_score_threshold": 3.0,
    "volume_z_threshold": 2.5,
    "volatility_tier": "moderate",
    "tier_multiplier": 1.0,
    "is_override": false
  }
}
```

## Implementation Details

### Services

#### ThresholdsService (`src/services/thresholds.service.ts`)
- Parses `config/thresholds.yaml` using the `yaml` package
- Caches the configuration for performance
- Provides methods to get full config or asset-specific thresholds
- Calculates effective thresholds based on tier multipliers and overrides

**Key Methods:**
- `loadConfig()`: Loads and caches YAML file
- `getConfig()`: Returns full threshold configuration
- `getAssetThresholds(symbol)`: Returns thresholds for specific asset
- `getAllAssetThresholds()`: Returns thresholds for all assets

#### SymbolsService (`src/services/symbols.service.ts`)
- Combines static symbol data with database statistics
- Queries Prisma for anomaly/narrative counts and price data
- Maps symbols to volatility tiers using shared constants

**Key Methods:**
- `getAllSymbols()`: Returns symbol list with tier info
- `getSymbolStats(symbol)`: Returns detailed stats for one symbol
- `getAllSymbolStats()`: Returns stats for all symbols

### Controllers

#### SymbolsController (`src/controllers/symbols.controller.ts`)
- `getAllSymbols`: Handler for GET /api/symbols
- `getSymbolStats`: Handler for GET /api/symbols/:symbol/stats
- `getAllSymbolStats`: Handler for GET /api/symbols/stats

#### ConfigController (`src/controllers/config.controller.ts`)
- `getThresholds`: Handler for GET /api/config/thresholds
- `getAssetThresholds`: Handler for GET /api/config/thresholds/:symbol

### Shared Types

Updated `web/shared/types/api.ts` with:
- `SymbolInfo`: Symbol metadata with tier and threshold info
- `SymbolStats`: Database statistics for a symbol
- `AssetThresholds`: Asset-specific threshold configuration
- `ThresholdConfig`: Full structure matching thresholds.yaml

### Supported Symbols

Added **PEPE-USD** to supported symbols (now 21 total):
- BTC-USD, ETH-USD (stable tier)
- DOGE-USD, SHIB-USD, PEPE-USD (volatile tier)
- 16 moderate tier symbols (SOL, XRP, ADA, etc.)

## Testing

All endpoints tested manually with curl:

```bash
# Start backend
cd web/backend
npm run dev

# Register/login to get auth cookie
curl -X POST http://localhost:4000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456"}' \
  -c cookies.txt

# Test endpoints
curl http://localhost:4000/api/symbols -b cookies.txt
curl http://localhost:4000/api/symbols/BTC-USD/stats -b cookies.txt
curl http://localhost:4000/api/symbols/stats -b cookies.txt
curl http://localhost:4000/api/config/thresholds -b cookies.txt
curl http://localhost:4000/api/config/thresholds/BTC-USD -b cookies.txt
```

See `web/backend/test-phase5.sh` for automated test script.

## Technical Notes

### TypeScript Configuration
Fixed `tsconfig.json` by removing `rootDir` restriction to support monorepo imports from `@mane/shared` package.

### Prisma Relations
Used correct Prisma relation name (`anomalies` not `anomaly`) for narrative count queries.

### YAML Parsing
Uses `yaml` package (v2.3.4) already installed in dependencies.

### Threshold Calculation Logic
1. Check for asset-specific override (highest priority)
2. Fall back to tier-based calculation (global_default × tier_multiplier)
3. Return all metadata: tier, multiplier, override flag, description

## Next Steps

**Phase 6: Dashboard Page** will use these endpoints to:
- Display symbol selector with tier badges
- Show anomaly counts per symbol
- Fetch threshold info for display in tooltips
- Filter anomalies by symbol volatility tier

## Files Modified/Created

**Created:**
- `web/backend/src/services/thresholds.service.ts`
- `web/backend/src/services/symbols.service.ts`
- `web/backend/src/controllers/symbols.controller.ts`
- `web/backend/src/controllers/config.controller.ts`
- `web/backend/src/routes/symbols.routes.ts`
- `web/backend/src/routes/config.routes.ts`
- `web/backend/src/schemas/config.schemas.ts`
- `web/backend/test-phase5.sh`

**Modified:**
- `web/backend/src/index.ts` (added new routes)
- `web/backend/tsconfig.json` (removed rootDir)
- `web/shared/types/api.ts` (updated types)
- `web/shared/constants/symbols.ts` (added PEPE-USD)
- `web/shared/constants/thresholds.ts` (added PEPE-USD)
- `web/IMPLEMENTATION_STATUS.md` (marked Phase 5 complete)
