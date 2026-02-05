# API Documentation

## Overview

This document covers the programmatic APIs for the Market Anomaly Narrative Engine. The system can be used in three ways:

1. **CLI** - Command-line interface (`mane` command)
2. **Python API** - Import and use modules directly
3. **REST API** - (Future) HTTP endpoints

## Python API

### Phase 1: Anomaly Detection

#### Importing Detectors

```python
from src.phase1_detector.anomaly_detection.statistical import (
    ZScoreDetector,
    BollingerBandDetector,
    VolumeSpikeDetector,
    CombinedDetector,
    AnomalyDetector,
)
```

#### ZScoreDetector

Detects price anomalies using Z-score on returns.

```python
detector = ZScoreDetector(threshold=3.0, window_minutes=60)
```

**Parameters**:
- `threshold` (float): Z-score threshold for detection (default: 3.0)
- `window_minutes` (int): Lookback window in minutes (default: 60)

**Methods**:

```python
def detect(
    prices: pd.DataFrame,
    current_time: Optional[datetime] = None
) -> List[DetectedAnomaly]:
    """Detect price anomalies using Z-score.

    Args:
        prices: DataFrame with columns [timestamp, price, volume, symbol]
        current_time: Time to check for anomaly (default: latest timestamp)

    Returns:
        List of DetectedAnomaly objects
    """
```

**Example**:

```python
import pandas as pd
from datetime import datetime, timedelta

# Create sample price data
prices = pd.DataFrame({
    'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
    'price': [45000 + i * 10 for i in range(60)],  # Gradual increase
    'volume': [1000] * 60,
    'symbol': ['BTC-USD'] * 60
})

# Add spike
prices.loc[55, 'price'] = 47000  # 4.4% spike

# Detect anomalies
detector = ZScoreDetector(threshold=3.0, window_minutes=60)
anomalies = detector.detect(prices)

for anomaly in anomalies:
    print(f"Type: {anomaly.anomaly_type}")
    print(f"Price change: {anomaly.price_change_pct:.2f}%")
    print(f"Z-score: {anomaly.z_score:.2f}")
    print(f"Confidence: {anomaly.confidence:.2f}")
```

**Output**:
```
Type: AnomalyType.PRICE_SPIKE
Price change: 4.40%
Z-score: 3.87
Confidence: 0.77
```

#### BollingerBandDetector

Detects price breakouts from Bollinger Bands.

```python
detector = BollingerBandDetector(window=20, std_multiplier=2.0)
```

**Parameters**:
- `window` (int): Rolling window size for SMA (default: 20)
- `std_multiplier` (float): Standard deviation multiplier (default: 2.0)

**Methods**:

```python
def detect(
    prices: pd.DataFrame,
    current_time: Optional[datetime] = None
) -> List[DetectedAnomaly]:
    """Detect price anomalies using Bollinger Bands."""
```

**Example**:

```python
detector = BollingerBandDetector(window=20, std_multiplier=2.0)
anomalies = detector.detect(prices)

if anomalies:
    anom = anomalies[0]
    print(f"Price broke {'upper' if anom.price_change_pct > 0 else 'lower'} band")
```

#### VolumeSpikeDetector

Detects unusual trading volume.

```python
detector = VolumeSpikeDetector(threshold=2.5, window_minutes=60)
```

**Parameters**:
- `threshold` (float): Z-score threshold for volume (default: 2.5)
- `window_minutes` (int): Lookback window in minutes (default: 60)

#### CombinedDetector

Detects combined price + volume anomalies (highest confidence).

```python
detector = CombinedDetector(
    price_threshold=2.0,
    volume_threshold=2.0,
    window_minutes=60
)
```

#### MultiTimeframeDetector

Detects cumulative price changes across multiple time windows (5/15/30/60 minutes).

```python
from src.phase1_detector.anomaly_detection.statistical import MultiTimeframeDetector

detector = MultiTimeframeDetector(
    threshold=3.0,
    timeframe_windows=[5, 15, 30, 60],  # Minutes
    baseline_multiplier=3  # Baseline = window × 3
)
anomalies = detector.detect(prices)
```

**Key Feature**: Catches "slow burn" cumulative moves that appear normal minute-by-minute.
- Example: DOGE +0.5%/min for 10 min = +5% total → NOW DETECTED ✓
- Without multi-timeframe: Each minute (Z-score ~0.8) looks normal → MISSED ✗

**Parameters**:
- `threshold` (float): Z-score threshold (default: 3.0)
- `timeframe_windows` (list): Time windows to analyze in parallel (default: [5, 15, 30, 60])
- `baseline_multiplier` (int): Baseline calculation (default: 3, meaning 60-min window uses 180-min baseline)

**Returns**: Highest confidence anomaly across all timeframes with `detection_metadata` dict:
```python
{
    "timeframe_minutes": 60,
    "volatility_tier": "stable",
    "asset_threshold": 3.5,
    "threshold_source": "asset_override",
    "detector": "MultiTimeframeDetector"
}
```

#### AnomalyDetector (Recommended)

Main detector orchestrating all strategies with multi-timeframe and asset-aware support.

```python
from config.settings import settings

detector = AnomalyDetector()  # Uses settings from config
anomalies = detector.detect_all(prices)
```

**Logic** (priority order):
1. `MultiTimeframeDetector` (if enabled) - priority 1
2. `CombinedDetector` (price + volume) - priority 2
3. Individual detectors (Z-score, Bollinger, volume) - priority 3

**Configuration** (`.env`):
```bash
DETECTION__ENABLE_MULTI_TIMEFRAME=true
DETECTION__USE_ASSET_SPECIFIC_THRESHOLDS=true
DETECTION__TIMEFRAME_WINDOWS=[5,15,30,60]
```

### Data Models

#### DetectedAnomaly

```python
from src.phase1_detector.anomaly_detection.models import DetectedAnomaly, AnomalyType

anomaly = DetectedAnomaly(
    symbol="BTC-USD",
    detected_at=datetime.now(),
    anomaly_type=AnomalyType.PRICE_SPIKE,
    z_score=3.5,
    price_change_pct=4.5,
    volume_change_pct=150.0,
    confidence=0.9,
    baseline_window_minutes=60,
    price_before=45000.0,
    price_at_detection=47025.0,
    volume_before=1000.0,
    volume_at_detection=2500.0
)
```

**Fields**:
- `symbol` (str): Crypto pair (e.g., "BTC-USD")
- `detected_at` (datetime): Timestamp of detection
- `anomaly_type` (AnomalyType): PRICE_SPIKE | PRICE_DROP | VOLUME_SPIKE | COMBINED
- `z_score` (float): Z-score from mean
- `price_change_pct` (float): Percentage price change
- `volume_change_pct` (float): Percentage volume change
- `confidence` (float): 0-1 confidence score
- `baseline_window_minutes` (int): Lookback period used
- `price_before` (float): Price before anomaly
- `price_at_detection` (float): Price at detection
- `volume_before` (float): Average volume before
- `volume_at_detection` (float): Volume at detection
- `detection_metadata` (dict, optional): Metadata about detection:
  - `timeframe_minutes` (int): Time window used (5/15/30/60)
  - `volatility_tier` (str): Asset tier (stable/moderate/volatile)
  - `asset_threshold` (float): Threshold used for this asset
  - `threshold_source` (str): Source of threshold (asset_override/tier/global)
  - `detector` (str): Detector class name

**Methods**:

```python
# Convert to dict
anomaly_dict = anomaly.model_dump()

# Convert to JSON
anomaly_json = anomaly.model_dump_json()

# Validate data
DetectedAnomaly.model_validate(data)
```

### Database Access

#### Using ORM Models

```python
from src.database.models import Anomaly, Narrative, Price
from src.database.connection import get_db_session

# Get session
db = get_db_session()

# Query anomalies
recent_anomalies = db.query(Anomaly)\
    .filter(Anomaly.detected_at > datetime.now() - timedelta(days=1))\
    .order_by(Anomaly.detected_at.desc())\
    .limit(10)\
    .all()

for anom in recent_anomalies:
    print(f"{anom.symbol}: {anom.price_change_pct:.2f}%")
    if anom.narrative:
        print(f"Narrative: {anom.narrative.narrative_text}")

db.close()
```

#### Using Context Manager

```python
from src.database.connection import get_db_context

with get_db_context() as db:
    # Auto-commits on success, rolls back on exception
    anomaly = Anomaly(
        symbol="BTC-USD",
        detected_at=datetime.now(),
        anomaly_type="price_spike",
        z_score=3.5,
        price_change_pct=4.5,
        confidence=0.9
    )
    db.add(anomaly)
    # Auto-committed when exiting context
```

### Asset-Aware Detection

#### AssetProfileManager

3-tier threshold lookup system for volatility-aware detection.

```python
from src.phase1_detector.anomaly_detection.asset_profiles import AssetProfileManager

manager = AssetProfileManager(config_path="config/thresholds.yaml")

# Get threshold for specific asset
threshold = manager.get_threshold("BTC-USD")
print(threshold)  # 3.5 (from asset override)

threshold = manager.get_threshold("DOGE-USD")
print(threshold)  # 2.0 (more sensitive for volatile asset)

threshold = manager.get_threshold("SOL-USD")
print(threshold)  # 3.0 (from tier multiplier)
```

**Lookup Priority**:
1. Asset-specific override (highest)
2. Volatility tier multiplier
3. Global default (lowest)

**Configuration** (`config/thresholds.yaml`):
```yaml
global_defaults:
  z_score_threshold: 3.0

volatility_tiers:
  stable: {multiplier: 1.2, assets: [BTC-USD, ETH-USD]}
  moderate: {multiplier: 1.0, assets: [SOL-USD, XRP-USD]}
  volatile: {multiplier: 0.7, assets: [DOGE-USD, SHIB-USD]}

asset_specific_thresholds:
  BTC-USD: {z_score_threshold: 3.5}
  DOGE-USD: {z_score_threshold: 2.0}
```

### Configuration

#### Loading Settings

```python
from config.settings import settings

# Access settings
print(settings.detection.z_score_threshold)  # 3.0
print(settings.detection.enable_multi_timeframe)  # true
print(settings.detection.price_history_lookback_minutes)  # 240 (CRITICAL!)
print(settings.llm.provider)  # 'anthropic'
print(settings.database.url)  # postgresql://...

# Modify at runtime (not persisted)
settings.detection.z_score_threshold = 4.0
```

**CRITICAL Configuration** ⚠️:
```python
# MUST be 240 for multi-timeframe detection
settings.orchestration.price_history_lookback_minutes = 240

# Why: 60-min window + (60 × 3 baseline) = 240 minutes minimum
# Setting to 60 caused major bug where 5-8% drops were missed!
```

#### Custom Settings

```python
from config.settings import Settings

# Load from specific env file
custom_settings = Settings(_env_file='.env.production')

# Override specific values
custom_settings = Settings(
    database__password="custom_password",
    llm__provider="openai"
)
```

## CLI API

### Commands

#### `mane init-db`

Initialize database schema.

```bash
mane init-db
```

**Output**:
```
Initializing database...
✓ Created table: prices
✓ Created table: anomalies
✓ Created table: news_articles
✓ Created table: news_clusters
✓ Created table: narratives
Database initialized successfully!
```

#### `mane detect`

Run anomaly detection for a single symbol or all symbols.

```bash
# Detect for single symbol
mane detect --symbol BTC-USD

# Detect for all configured symbols
mane detect --all
```

**Options**:
- `--symbol TEXT` - Crypto symbol to analyze (e.g., BTC-USD)
- `--all` - Run detection for all configured symbols

**Output** (single symbol):
```
Detecting anomalies for BTC-USD...

╭─────────────────────── Anomaly Detected: BTC-USD ───────────────────────╮
│ Type: price_drop                                                         │
│ Confidence: 0.89                                                         │
│ Price Change: -5.20%                                                     │
│ Z-Score: -3.87                                                           │
│                                                                          │
│ Narrative:                                                               │
│ Bitcoin dropped 5.2% following SEC announcement of stricter             │
│ cryptocurrency regulations. The negative sentiment across social        │
│ media amplified the sell-off.                                           │
│                                                                          │
│ Validation: ✓ Passed (score: 0.78)                                      │
│ Tools Used: verify_timestamp, sentiment_check, check_social_sentiment   │
│ Generation Time: 3.45s                                                   │
│ News Articles: 12                                                        │
│ Clusters: 3                                                              │
╰──────────────────────────────────────────────────────────────────────────╯
```

#### `mane serve`

Start continuous anomaly detection scheduler.

```bash
mane serve
```

Runs two periodic jobs:
- **Price storage**: Every 60 seconds (stores current prices for all symbols)
- **Detection cycle**: Every `DETECTION__POLL_INTERVAL_SECONDS` (default: 300 seconds)

Press `Ctrl+C` to gracefully stop the scheduler.

**Output**:
```
╭────────────── Market Anomaly Narrative Engine ──────────────╮
│ Status: Starting scheduler...                               │
│ Monitoring: 5 symbols (BTC-USD, ETH-USD, SOL-USD, ...)     │
│ Poll Interval: 300 seconds                                  │
│ Press Ctrl+C to stop                                        │
╰─────────────────────────────────────────────────────────────╯

[14:30:00] Storing prices for 5 symbols...
[14:30:01] ✓ Stored prices for all symbols
[14:35:00] Running detection cycle...
[14:35:02] BTC-USD: No anomaly detected
[14:35:04] ETH-USD: ✓ Anomaly detected (narrative generated)
[14:35:06] SOL-USD: No anomaly detected
[14:35:08] MATIC-USD: No anomaly detected
[14:35:10] AVAX-USD: No anomaly detected
[14:40:00] Storing prices for 5 symbols...
...
^C
[14:42:15] Shutdown signal received
[14:42:15] Stopping scheduler gracefully...
[14:42:15] Scheduler stopped successfully
```

#### `mane list-narratives`

Query and display generated narratives.

```bash
# Show recent narratives (table format)
mane list-narratives --limit 10

# Filter by symbol
mane list-narratives --symbol BTC-USD --limit 5

# Show only validated narratives
mane list-narratives --validated-only

# JSON output for programmatic use
mane list-narratives --format json --limit 5
```

**Options**:
- `--limit INT` - Number of narratives to show (default: 10)
- `--symbol TEXT` - Filter by crypto symbol
- `--validated-only` - Show only validated narratives
- `--format [table|json]` - Output format (default: table)

**Output** (table):
```
Recent Narratives
┌────────────────────┬─────────┬─────────────────────────────┬────────────┐
│ Timestamp          │ Symbol  │ Narrative                   │ Validation │
├────────────────────┼─────────┼─────────────────────────────┼────────────┤
│ 2024-01-15 14:15   │ BTC-USD │ Bitcoin dropped 5.2% at...  │ ✓ Passed   │
│ 2024-01-15 13:42   │ ETH-USD │ Ethereum surged 3.1% on...  │ ✓ Passed   │
│ 2024-01-15 12:30   │ SOL-USD │ Cause unknown for 2.8%...   │ ✗ Failed   │
└────────────────────┴─────────┴─────────────────────────────┴────────────┘
```

**Output** (JSON):
```json
[
  {
    "id": "uuid-1234",
    "symbol": "BTC-USD",
    "detected_at": "2024-01-15T14:15:00Z",
    "narrative_text": "Bitcoin dropped 5.2% following SEC announcement...",
    "validation_passed": true,
    "validation_score": 0.78,
    "anomaly_type": "price_drop",
    "price_change_pct": -5.2,
    "confidence": 0.89
  }
]
```

#### `mane metrics`

Display scheduler performance metrics.

```bash
# Table format
mane metrics

# JSON format
mane metrics --format json
```

**Options**:
- `--format [table|json]` - Output format (default: table)

**Output** (table):
```
Scheduler Metrics
┌────────────────────────┬────────┐
│ Metric                 │ Value  │
├────────────────────────┼────────┤
│ Total Detections       │ 142    │
│ Successful             │ 98     │
│ Failed                 │ 12     │
│ Rejected (validation)  │ 32     │
│ Success Rate           │ 69.0%  │
│ Validation Pass Rate   │ 75.4%  │
└────────────────────────┴────────┘

Per-Symbol Metrics
┌─────────┬────────────┬───────────┬──────────┬──────────────┐
│ Symbol  │ Detections │ Successes │ Failures │ Success Rate │
├─────────┼────────────┼───────────┼──────────┼──────────────┤
│ BTC-USD │ 35         │ 28        │ 2        │ 80.0%        │
│ ETH-USD │ 32         │ 25        │ 3        │ 78.1%        │
│ SOL-USD │ 28         │ 18        │ 4        │ 64.3%        │
└─────────┴────────────┴───────────┴──────────┴──────────────┘
```

**Output** (JSON):
```json
{
  "total_detections": 142,
  "successful_detections": 98,
  "failed_detections": 12,
  "rejected_validations": 32,
  "success_rate": 0.69,
  "validation_pass_rate": 0.754,
  "symbols": {
    "BTC-USD": {
      "total_runs": 35,
      "successful_runs": 28,
      "failed_runs": 2,
      "rejected_validations": 5,
      "success_rate": 0.8
    }
  }
}
```

#### `mane backfill`

Backfill historical price data from exchanges.

```bash
# Single symbol
mane backfill --symbol BTC-USD --days 7

# All symbols
mane backfill --all --days 30
```

**Options**:
- `--symbol TEXT` - Crypto symbol to backfill (e.g., BTC-USD)
- `--all` - Backfill all configured symbols
- `--days INT` - Number of days to backfill (default: 7)

**Output**:
```
Backfilling BTC-USD prices for 7 days...
Fetching 10,080 1-minute candles (7 days × 1,440 minutes)
Progress: ████████████████████ 100% (10,080/10,080)
✓ Stored 9,823 new prices (257 duplicates skipped)
Completed in 12.3 seconds
```

#### `mane backfill-news`

Create historical news datasets for replay mode testing.

```bash
mane backfill-news --symbol BTC-USD \
  --start-date 2024-03-14 \
  --end-date 2024-03-14 \
  --file-path datasets/news/btc_mar14.json
```

**Options**:
- `--symbol TEXT` - Crypto symbol (required)
- `--start-date DATE` - Start date (YYYY-MM-DD, required)
- `--end-date DATE` - End date (YYYY-MM-DD, required)
- `--file-path PATH` - Output JSON file path (required)
- `--sources LIST` - News sources to use (default: all enabled sources)

**Output Format** (JSON):
```json
{
  "metadata": {
    "symbol": "BTC-USD",
    "start_date": "2024-03-14",
    "end_date": "2024-03-14",
    "created_at": "2024-01-15T14:30:00Z",
    "article_count": 147
  },
  "articles": [
    {
      "title": "Bitcoin Surges Past $70,000",
      "source": "CoinDesk",
      "url": "https://...",
      "published_at": "2024-03-14T10:30:00Z",
      "summary": "Bitcoin reached a new all-time high...",
      "sentiment": "positive"
    }
  ]
}
```

**Usage with Replay Mode**:
```bash
# 1. Create dataset
mane backfill-news --symbol BTC-USD --start-date 2024-03-14 --end-date 2024-03-14 --file-path datasets/news/my_news.json

# 2. Run detection in replay mode
mane detect --symbol BTC-USD --news-mode replay

# 3. Or hybrid mode (combines live + replay)
mane detect --symbol BTC-USD --news-mode hybrid
```

## REST API

The REST API is **fully implemented** and production-ready. See `docs/API_REFERENCE.md` for complete documentation.

**Base URL**: `http://localhost:3001` (development)

**Quick Overview**:

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Login (returns JWT in httpOnly cookie)
- `POST /auth/logout` - Logout
- `GET /auth/me` - Get current user

### Anomalies
- `GET /api/anomalies` - List anomalies with filtering/pagination
- `GET /api/anomalies/:id` - Get anomaly details with news and prices

### News
- `GET /api/news` - List news articles with filtering

### Prices
- `GET /api/prices` - Get price history for charting
- `GET /api/prices/latest` - Get latest price

### Symbols
- `GET /api/symbols` - List supported symbols

### Configuration
- `GET /api/config/thresholds` - Get detection thresholds
- `GET /api/config/settings` - Get system settings

### Health
- `GET /health` - System health check

**Example**:
```bash
# Login
curl -X POST http://localhost:3001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' \
  -c cookies.txt

# Get anomalies
curl http://localhost:3001/api/anomalies?symbol=BTC-USD&limit=10 \
  -b cookies.txt

# Get anomaly details
curl http://localhost:3001/api/anomalies/550e8400-e29b-41d4-a716-446655440000 \
  -b cookies.txt
```

**See complete API reference**: `docs/API_REFERENCE.md`

## Error Handling

### Common Exceptions

```python
from src.utils.exceptions import (
    DetectorError,
    DataInsufficientError,
    ConfigurationError
)

try:
    anomalies = detector.detect(prices)
except DataInsufficientError as e:
    print(f"Not enough data: {e}")
except DetectorError as e:
    print(f"Detection failed: {e}")
```

### Database Exceptions

```python
from sqlalchemy.exc import IntegrityError, OperationalError

try:
    with get_db_context() as db:
        db.add(anomaly)
except IntegrityError:
    print("Duplicate anomaly ID")
except OperationalError:
    print("Database connection failed")
```

## Rate Limiting (Future)

When using external APIs:

```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=60)  # 10 calls per minute
def fetch_news():
    # API call
    pass
```

## Async Support (Future)

For concurrent processing:

```python
import asyncio

async def detect_all_symbols():
    symbols = settings.detection.symbols
    tasks = [detect_symbol(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return results

# Run
results = asyncio.run(detect_all_symbols())
```

---

**Next Steps**:
- Implement data ingestion APIs
- Build LLM agent APIs
- Create REST API with FastAPI
