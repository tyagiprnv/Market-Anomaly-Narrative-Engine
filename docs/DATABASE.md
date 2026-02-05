# Database Schema Documentation

## Overview

The Market Anomaly Narrative Engine uses PostgreSQL for reliable time-series storage and complex relational queries. The schema is designed to efficiently track:

1. **Price data** - Raw time-series from crypto exchanges
2. **Anomalies** - Statistically detected market events
3. **News articles** - Context around anomalies
4. **Narratives** - AI-generated explanations
5. **Clusters** - Grouped related news

## Entity Relationship Diagram

```
┌─────────────┐
│   Prices    │
└─────────────┘
       │
       │ Used for detection
       ▼
┌─────────────────────────────────────┐
│           Anomalies                 │
│  ┌──────────────────────────────┐  │
│  │ id (UUID)                    │  │
│  │ symbol (VARCHAR)             │  │
│  │ detected_at (TIMESTAMP)      │  │
│  │ anomaly_type (ENUM)          │  │
│  │ z_score (FLOAT)              │  │
│  │ price_change_pct (FLOAT)     │  │
│  │ confidence (FLOAT)           │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
       │                    │
       │                    │
       ▼                    ▼
┌──────────────┐    ┌──────────────────┐
│NewsArticles  │    │  NewsCluster     │
│              │    │                  │
│- title       │    │- cluster_number  │
│- published_at│    │- centroid        │
│- cluster_id  │    │- sentiment       │
└──────────────┘    └──────────────────┘
       │
       │ Explained by
       ▼
┌─────────────────────────────┐
│        Narratives           │
│                             │
│ - narrative_text (TEXT)     │
│ - validation_passed (BOOL)  │
│ - llm_provider (VARCHAR)    │
│ - tools_used (JSON)         │
└─────────────────────────────┘
```

## Table Definitions

### 1. `prices`

**Purpose**: Store raw time-series price data from crypto exchanges.

```sql
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price FLOAT NOT NULL,
    volume_24h FLOAT,
    high_24h FLOAT,
    low_24h FLOAT,
    bid FLOAT,
    ask FLOAT,
    source VARCHAR(20),  -- 'coinbase', 'binance'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_symbol_timestamp ON prices(symbol, timestamp);
```

**Key Fields**:
- `symbol`: Crypto pair (e.g., "BTC-USD")
- `timestamp`: Price observation time (UTC)
- `price`: Current price in quote currency
- `volume_24h`: 24-hour trading volume
- `source`: Data provider

**Indexes**:
- `idx_symbol_timestamp`: Optimizes time-series queries like "last hour of BTC prices"

**Retention**: Archive data older than 30 days (configurable).

---

### 2. `anomalies`

**Purpose**: Store detected statistical anomalies.

```sql
CREATE TABLE anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    anomaly_type VARCHAR(20) NOT NULL
        CHECK (anomaly_type IN ('price_spike', 'price_drop', 'volume_spike', 'combined')),

    -- Statistical metrics
    z_score FLOAT,
    price_change_pct FLOAT,
    volume_change_pct FLOAT,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    baseline_window_minutes INTEGER,

    -- Price snapshot
    price_before FLOAT,
    price_at_detection FLOAT,
    volume_before FLOAT,
    volume_at_detection FLOAT,

    -- Detection metadata (NEW in v0.2)
    detection_metadata JSON,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_symbol_detected ON anomalies(symbol, detected_at DESC);
```

**Key Fields**:
- `id`: UUID for unique identification
- `anomaly_type`: Type of anomaly detected
  - `price_spike`: Price jumped (positive z-score)
  - `price_drop`: Price crashed (negative z-score)
  - `volume_spike`: Unusual trading volume
  - `combined`: Both price and volume anomaly (highest confidence)
- `z_score`: How many standard deviations from mean
- `confidence`: 0-1 score (higher = more significant)
- `baseline_window_minutes`: Lookback period used for detection
- `detection_metadata` (JSON): Metadata about detection method (NEW in v0.2)

**Detection Metadata Structure**:
```json
{
  "timeframe_minutes": 60,
  "volatility_tier": "stable",
  "asset_threshold": 3.5,
  "threshold_source": "asset_override",
  "detector": "MultiTimeframeDetector"
}
```

**Fields**:
- `timeframe_minutes` (int): Time window used (5/15/30/60 minutes)
- `volatility_tier` (string): Asset classification (stable/moderate/volatile)
- `asset_threshold` (float): Actual threshold applied for this asset
- `threshold_source` (string): Where threshold came from:
  - `asset_override` - From config/thresholds.yaml asset_specific_thresholds
  - `tier` - From volatility tier multiplier
  - `global` - From global defaults
- `detector` (string): Detector class name (MultiTimeframeDetector, ZScoreDetector, etc.)

**Indexes**:
- `idx_symbol_detected`: Fast lookups for recent anomalies per symbol

---

### 3. `news_articles`

**Purpose**: Store news articles linked to anomalies.

```sql
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id UUID REFERENCES anomalies(id) ON DELETE CASCADE,

    source VARCHAR(50),  -- 'cryptopanic', 'newsapi', 'reddit'
    title TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMP NOT NULL,
    summary TEXT,

    -- Clustering
    cluster_id INTEGER,  -- -1 for unclustered
    embedding JSON,      -- 384-dim vector as JSON array

    -- Timing
    timing_tag VARCHAR(20),  -- 'pre_event' or 'post_event'
    time_diff_minutes FLOAT, -- ±minutes from anomaly

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_anomaly ON news_articles(anomaly_id);
CREATE INDEX idx_published ON news_articles(published_at);
```

**Key Fields**:
- `anomaly_id`: Foreign key to parent anomaly
- `timing_tag`: Whether news came before or after anomaly
  - `pre_event`: News published before anomaly (potential cause)
  - `post_event`: News published after anomaly (reaction reporting)
- `cluster_id`: Which cluster this article belongs to (-1 = noise)
- `embedding`: Sentence-transformer embedding (for similarity search)

**On Delete Cascade**: Deleting an anomaly removes all linked news.

---

### 4. `news_clusters`

**Purpose**: Group related news articles.

```sql
CREATE TABLE news_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id UUID REFERENCES anomalies(id) ON DELETE CASCADE,
    cluster_number INTEGER,  -- -1 for noise

    article_ids JSON,         -- List of article UUIDs
    centroid_summary TEXT,    -- Representative headline
    dominant_sentiment FLOAT, -- -1 (negative) to +1 (positive)
    size INTEGER,             -- Number of articles

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cluster_anomaly ON news_clusters(anomaly_id);
```

**Key Fields**:
- `cluster_number`: Cluster ID from HDBSCAN (-1 = unclustered noise)
- `article_ids`: JSON array of article UUIDs in this cluster
- `centroid_summary`: Most representative headline (closest to centroid)
- `dominant_sentiment`: Average sentiment score across articles

---

### 6. `backfill_progress`

**Purpose**: Track historical data backfill state (prevents duplicate work).

```sql
CREATE TABLE backfill_progress (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    data_type VARCHAR(20) NOT NULL,  -- 'prices' or 'news'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,     -- 'in_progress', 'completed', 'failed'
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backfill_symbol_type ON backfill_progress(symbol, data_type);
CREATE INDEX idx_backfill_status ON backfill_progress(status);
```

**Key Fields**:
- `symbol`: Crypto pair being backfilled
- `data_type`: Type of data (`prices` or `news`)
- `start_date` / `end_date`: Date range being backfilled
- `status`: Current backfill status
  - `in_progress`: Currently running
  - `completed`: Successfully finished
  - `failed`: Encountered error
- `records_processed`: Number of records inserted
- `error_message`: Error details if status = 'failed'

**Purpose**: Enables:
- Resume interrupted backfills
- Track backfill history
- Prevent duplicate backfills for same date range
- Monitor backfill performance

---

### 5. `narratives`

**Purpose**: Store AI-generated explanations of anomalies.

```sql
CREATE TABLE narratives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id UUID UNIQUE REFERENCES anomalies(id) ON DELETE CASCADE,

    -- Agent output
    narrative_text TEXT NOT NULL,
    confidence_score FLOAT,

    -- Tool usage tracking
    tools_used JSON,     -- ["verify_timestamp", "sentiment_check", ...]
    tool_results JSON,   -- Aggregated tool outputs

    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validation_passed BOOLEAN,
    validation_reason TEXT,

    -- LLM metadata
    llm_provider VARCHAR(20),  -- 'openai', 'anthropic', 'ollama'
    llm_model VARCHAR(50),
    generation_time_seconds FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP
);

CREATE INDEX idx_narrative_anomaly ON narratives(anomaly_id);
CREATE INDEX idx_narrative_validated ON narratives(validation_passed);
```

**Key Fields**:
- `narrative_text`: The 2-sentence explanation (max 500 tokens)
- `tools_used`: Which agent tools were called
- `validation_passed`: TRUE if passed Phase 3 validation
- `validation_reason`: Why validation failed (if applicable)
- `llm_provider`: Which LLM generated this

**Constraints**:
- `anomaly_id` is UNIQUE: One narrative per anomaly
- `validation_passed` can be NULL (not yet validated)

---

## Common Queries

### 1. Get Recent Anomalies with Narratives and Detection Metadata

```sql
SELECT
    a.symbol,
    a.detected_at,
    a.anomaly_type,
    a.price_change_pct,
    a.confidence,
    a.detection_metadata,
    a.detection_metadata->>'detector' AS detector_name,
    a.detection_metadata->>'timeframe_minutes' AS timeframe,
    n.narrative_text,
    n.validation_passed
FROM anomalies a
LEFT JOIN narratives n ON a.id = n.anomaly_id
WHERE a.detected_at > NOW() - INTERVAL '24 hours'
ORDER BY a.detected_at DESC
LIMIT 20;
```

### 1b. Filter Anomalies by Multi-Timeframe Detector

```sql
SELECT *
FROM anomalies
WHERE detection_metadata->>'detector' = 'MultiTimeframeDetector'
  AND (detection_metadata->>'timeframe_minutes')::int = 60
  AND detected_at > NOW() - INTERVAL '7 days';
```

### 2. Find Anomalies with High-Confidence News Clusters

```sql
SELECT
    a.symbol,
    a.detected_at,
    nc.size AS cluster_size,
    nc.centroid_summary,
    nc.dominant_sentiment
FROM anomalies a
JOIN news_clusters nc ON a.id = nc.anomaly_id
WHERE nc.size >= 3  -- At least 3 articles in cluster
  AND nc.cluster_number != -1  -- Not noise
ORDER BY a.detected_at DESC;
```

### 3. Analyze Validation Success Rate

```sql
SELECT
    llm_provider,
    COUNT(*) AS total_narratives,
    SUM(CASE WHEN validation_passed THEN 1 ELSE 0 END) AS passed,
    ROUND(100.0 * SUM(CASE WHEN validation_passed THEN 1 ELSE 0 END) / COUNT(*), 2) AS pass_rate
FROM narratives
WHERE validated = TRUE
GROUP BY llm_provider;
```

### 4. Find Similar Historical Anomalies

```sql
SELECT
    a.symbol,
    a.detected_at,
    a.price_change_pct,
    n.narrative_text
FROM anomalies a
JOIN narratives n ON a.id = n.anomaly_id
WHERE a.symbol = 'BTC-USD'
  AND a.anomaly_type = 'price_drop'
  AND a.price_change_pct BETWEEN -6.0 AND -4.0  -- Similar magnitude
  AND a.detected_at > NOW() - INTERVAL '90 days'
ORDER BY a.detected_at DESC;
```

### 5. Get Price History Around Anomaly

```sql
-- Get 1 hour of prices before and after anomaly
WITH anomaly_time AS (
    SELECT detected_at FROM anomalies WHERE id = 'some-uuid'
)
SELECT
    p.timestamp,
    p.price,
    p.volume_24h
FROM prices p, anomaly_time at
WHERE p.symbol = 'BTC-USD'
  AND p.timestamp BETWEEN at.detected_at - INTERVAL '1 hour'
                      AND at.detected_at + INTERVAL '1 hour'
ORDER BY p.timestamp;
```

## Data Retention Policy

**Recommendation**:
- **prices**: Keep 30 days, archive older data
- **anomalies**: Keep indefinitely (small size)
- **news_articles**: Keep indefinitely (useful for search_historical tool)
- **narratives**: Keep indefinitely
- **news_clusters**: Keep indefinitely

**Archive Strategy**:
```sql
-- Archive old prices (run daily)
DELETE FROM prices
WHERE created_at < NOW() - INTERVAL '30 days';
```

## Performance Optimization

### Indexing Strategy

1. **Time-series queries**: `(symbol, timestamp)` composite index
2. **Foreign keys**: Auto-indexed by PostgreSQL
3. **Full-text search**: Use `pg_trgm` for narrative search

```sql
-- Enable trigram extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add GIN index for narrative search
CREATE INDEX idx_narrative_text_gin ON narratives
USING GIN (narrative_text gin_trgm_ops);

-- Fast fuzzy search
SELECT * FROM narratives
WHERE narrative_text % 'SEC enforcement'  -- Similarity search
ORDER BY similarity(narrative_text, 'SEC enforcement') DESC
LIMIT 10;
```

### Partitioning (Future)

For production scale, partition `prices` by month:

```sql
CREATE TABLE prices (
    -- ... columns
) PARTITION BY RANGE (timestamp);

CREATE TABLE prices_2024_01 PARTITION OF prices
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

## Web Backend (Prisma ORM)

The web backend uses **Prisma** which introspects the Python-owned PostgreSQL schema.

**Setup Process**:

```bash
cd web/backend

# 1. Introspect existing database (reads schema created by Python)
npx prisma db pull

# 2. Generate Prisma client (TypeScript types)
npx prisma generate
```

**Generated Schema** (`web/backend/prisma/schema.prisma`):
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Anomaly {
  id                  String    @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  symbol              String    @db.VarChar(20)
  detected_at         DateTime
  anomaly_type        String    @db.VarChar(20)
  z_score             Float?
  price_change_pct    Float?
  confidence          Float?
  detection_metadata  Json?     // Maps to JSON column

  narrative           Narrative?
  news_articles       NewsArticle[]
  news_clusters       NewsCluster[]

  @@index([symbol, detected_at])
  @@map("anomalies")
}

// ... other models
```

**Usage in TypeScript**:
```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Query with type safety
const anomalies = await prisma.anomaly.findMany({
  where: {
    symbol: 'BTC-USD',
    detection_metadata: {
      path: ['detector'],
      equals: 'MultiTimeframeDetector'
    }
  },
  include: { narrative: true },
  orderBy: { detected_at: 'desc' },
});

// detection_metadata is typed as Prisma.JsonValue
const metadata = anomalies[0].detection_metadata as {
  timeframe_minutes: number;
  volatility_tier: string;
};
```

**Key Points**:
- Schema is **read-only** for Prisma (Python owns it)
- Never run `prisma db push` or `prisma migrate` (would conflict with Python)
- Re-run `prisma db pull` after Python schema changes
- Prisma provides type-safe queries in TypeScript

---

## Migrations with Alembic (Python)

### Initial Migration

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### Schema Changes

When modifying `src/database/models.py`:

```bash
# Generate migration
alembic revision --autogenerate -m "Add detection_metadata column"

# Review migration file in alembic/versions/
# Apply migration
alembic upgrade head

# IMPORTANT: After applying, regenerate Prisma client
cd web/backend
npx prisma db pull      # Pull updated schema
npx prisma generate     # Regenerate TypeScript types
```

## Backup & Restore

### Backup

```bash
# Backup entire database
pg_dump mane_db > backup_$(date +%Y%m%d).sql

# Backup specific table
pg_dump -t anomalies mane_db > anomalies_backup.sql
```

### Restore

```bash
# Restore from backup
psql mane_db < backup_20240115.sql
```

## Connection Pooling

The application uses SQLAlchemy's connection pool:

```python
# From src/database/connection.py
engine = create_engine(
    database_url,
    pool_size=10,        # Maintain 10 connections
    max_overflow=20,     # Allow 20 additional connections
    pool_pre_ping=True,  # Verify connections before use
)
```

**Best Practices**:
- Keep pool_size small for development (5-10)
- Increase for production based on concurrent users
- Monitor connection usage: `SELECT count(*) FROM pg_stat_activity;`

## Security

1. **Never commit database passwords** - Use `.env` files
2. **Use read-only users** for analytics queries
3. **Enable SSL** for production connections

```python
# SSL connection
engine = create_engine(
    database_url,
    connect_args={'sslmode': 'require'}
)
```

---

**Next Steps**:
- Set up Alembic migrations
- Configure backups
- Implement data archival cron job
