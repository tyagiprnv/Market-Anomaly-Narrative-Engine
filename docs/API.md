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

#### AnomalyDetector (Recommended)

Main detector orchestrating all strategies.

```python
from config.settings import settings

detector = AnomalyDetector()  # Uses settings from config
anomalies = detector.detect_all(prices)
```

**Logic**:
1. Checks `CombinedDetector` first (price + volume)
2. Falls back to individual detectors if no combined anomaly
3. Returns highest confidence anomaly

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

### Configuration

#### Loading Settings

```python
from config.settings import settings

# Access settings
print(settings.detection.z_score_threshold)  # 3.0
print(settings.llm.provider)  # 'anthropic'
print(settings.database.url)  # postgresql://...

# Modify at runtime (not persisted)
settings.detection.z_score_threshold = 4.0
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

#### `mane detect` (Future)

Run anomaly detection for a single symbol.

```bash
mane detect --symbol BTC-USD

# Options:
#   --symbol TEXT    Crypto symbol to analyze (default: BTC-USD)
#   --threshold FLOAT Override detection threshold
#   --window INT     Lookback window in minutes
```

**Output**:
```
Detecting anomalies for BTC-USD...
✓ Anomaly detected: PRICE_DROP
  Price change: -5.2%
  Z-score: -3.87
  Confidence: 0.89
  Detected at: 2024-01-15 14:15:00 UTC

Narrative: Bitcoin dropped 5.2% at 2:15 PM UTC. The move followed news of SEC enforcement action against a major exchange.
```

#### `mane serve` (Future)

Start scheduled anomaly detection service.

```bash
mane serve

# Runs detection every 60 seconds (configurable via POLL_INTERVAL_SECONDS)
# Press Ctrl+C to stop
```

#### `mane list-narratives` (Future)

List recent generated narratives.

```bash
mane list-narratives --limit 10

# Options:
#   --limit INT      Number of narratives to show (default: 10)
#   --symbol TEXT    Filter by symbol
#   --validated BOOL Show only validated narratives
```

**Output** (table):
```
┌────────────────────┬────────┬─────────────────────────────┬───────────┐
│ Timestamp          │ Symbol │ Narrative                   │ Validated │
├────────────────────┼────────┼─────────────────────────────┼───────────┤
│ 2024-01-15 14:15   │ BTC    │ Bitcoin dropped 5.2% at...  │ ✓         │
│ 2024-01-15 13:42   │ ETH    │ Ethereum surged 3.1% on...  │ ✓         │
│ 2024-01-15 12:30   │ SOL    │ Anomaly Detected (Unknown)  │ ✗         │
└────────────────────┴────────┴─────────────────────────────┴───────────┘
```

#### `mane backfill` (Future)

Backfill historical price data.

```bash
mane backfill --days 30 --symbol BTC-USD

# Options:
#   --days INT       Number of days to backfill (default: 7)
#   --symbol TEXT    Crypto symbol (default: all symbols)
```

## REST API (Future)

### Planned Endpoints

#### GET /anomalies

Get recent anomalies.

**Request**:
```http
GET /anomalies?symbol=BTC-USD&limit=10
```

**Response**:
```json
{
  "anomalies": [
    {
      "id": "uuid",
      "symbol": "BTC-USD",
      "detected_at": "2024-01-15T14:15:00Z",
      "anomaly_type": "price_drop",
      "price_change_pct": -5.2,
      "z_score": -3.87,
      "confidence": 0.89,
      "narrative": {
        "text": "Bitcoin dropped 5.2% at 2:15 PM UTC...",
        "validated": true
      }
    }
  ],
  "total": 1
}
```

#### POST /detect

Manually trigger detection for a symbol.

**Request**:
```http
POST /detect
Content-Type: application/json

{
  "symbol": "BTC-USD",
  "threshold": 3.0
}
```

**Response**:
```json
{
  "anomaly": {...},
  "narrative": "...",
  "validation_passed": true
}
```

#### GET /narratives/{id}

Get specific narrative.

**Request**:
```http
GET /narratives/uuid
```

**Response**:
```json
{
  "id": "uuid",
  "anomaly_id": "uuid",
  "narrative_text": "Bitcoin dropped 5.2%...",
  "validation_passed": true,
  "tools_used": ["verify_timestamp", "sentiment_check"],
  "llm_provider": "anthropic",
  "created_at": "2024-01-15T14:15:30Z"
}
```

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
