# Market Anomaly Narrative Engine (MANE)

**Detect crypto price anomalies. Explain why they happened. Never hallucinate.**

MANE solves a critical problem in quantitative finance: dashboards tell you *what* changed, but rarely *why*. Traditional LLMs hallucinate connections between unrelated events. MANE doesn't.

**How it works:**
1. **Statistical Detection** - Z-score, Bollinger Bands, volume spikes (deterministic)
2. **Time-Windowed News** - Links anomalies to news within ±30 minutes (causal filtering)
3. **AI Investigation** - LLM agent with tools investigates and writes 2-sentence narratives
4. **Validation** - Rules + Judge LLM verify plausibility (or return "Unknown")

> **Architecture Philosophy**: Workflow first (predictable), Agent second (reasoning)

## Status

**✅ Phase 1 Complete**: Statistical detectors (Z-score, Bollinger, volume, combined) · PostgreSQL schema · Settings management · Price ingestion (Coinbase, Binance) · News aggregation (CryptoPanic, Reddit, NewsAPI) · News clustering (sentence-transformers + HDBSCAN)

**⏳ Next: Phase 2**: LLM agent with 5 tools · Narrative generation · Validation engine · CLI · Scheduler

**Progress**: 8/17 components complete (47%)

## Quick Start

**Prerequisites**: Python 3.13+ · [uv](https://github.com/astral-sh/uv) · PostgreSQL 14+ · LLM API key

```bash
# Clone and setup
git clone https://github.com/your-org/market-anomaly-narrative-engine.git
cd market-anomaly-narrative-engine
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Setup database (Docker or local)
docker run --name mane-postgres -e POSTGRES_PASSWORD=yourpass -p 5432:5432 -d postgres:14

# Configure environment
cp .env.example .env
# Edit .env with: DATABASE__PASSWORD, ANTHROPIC_API_KEY (or OPENAI_API_KEY)

# Initialize database (when implemented)
mane init-db

# Run detection (when implemented)
mane detect --symbol BTC-USD  # Detect anomalies for Bitcoin
mane serve                     # Start scheduled detection (every 60s)
mane list-narratives --limit 10  # View recent narratives
```

## Architecture

### Three-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: DETECTOR                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Price Data   │───▶│  Statistical │───▶│     News     │       │
│  │  Ingestion   │    │   Detection  │    │  Clustering  │       │
│  │(Coinbase API)│    │(Z-score, BB) │    │ (HDBSCAN)    │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         ▼                    ▼                    ▼             │
│    [Price DB] ──────▶ [Anomalies] ◀────── [News Articles]       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 2: JOURNALIST                           │
│                                                                 │
│              ┌─────────────────────────┐                        │
│              │   LLM Agent (LiteLLM)   │                        │
│              │  ┌──────────────────┐   │                        │
│              │  │ verify_timestamp │   │                        │
│              │  │ sentiment_check  │   │                        │
│              │  │search_historical │◀──┼─── Tool Loop           │
│              │  │  market_context  │   │                        │
│              │  │ social_sentiment │   │                        │
│              │  └──────────────────┘   │                        │
│              └─────────────────────────┘                        │
│                          │                                      │
│                          ▼                                      │
│                  [2-Sentence Narrative]                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: SKEPTIC                             │
│                                                                 │
│    ┌─────────────────┐         ┌─────────────────┐              │
│    │  Rule-Based     │         │   Judge LLM     │              │
│    │  Validation     │────┬───▶│   Validation    │              │
│    │ - Sentiment ✓   │    │    │ - Plausibility  │              │
│    │ - Magnitude ✓   │    │    │ - Causality     │              │
│    │ - Timing ✓      │    │    │ - Coherence     │              │
│    └─────────────────┘    │    └─────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│                  ┌─────────────────┐                            │
│                  │   VALID  ✓      │                            │
│                  │   or            │                            │
│                  │   "Unknown"     │                            │
│                  └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/
├── phase1_detector/        # ✅ Statistical detection, news aggregation, clustering
│   ├── anomaly_detection/  # ✅ Z-score, Bollinger, volume, combined detectors
│   ├── data_ingestion/     # ✅ Coinbase & Binance API clients
│   ├── news_aggregation/   # ✅ CryptoPanic, Reddit, NewsAPI clients
│   └── clustering/         # ✅ sentence-transformers + HDBSCAN
├── phase2_journalist/      # ⏳ LLM agent with 5 tools (timestamp, sentiment, etc.)
├── phase3_skeptic/         # ⏳ Rule-based + Judge LLM validation
├── database/               # ✅ SQLAlchemy ORM (prices → anomalies → narratives)
├── llm/                    # ⏳ LiteLLM wrapper (OpenAI, Anthropic, Ollama)
└── orchestration/          # ⏳ Pipeline coordinator & scheduler
```

## Configuration

**Database Schema**: `prices` (time-series data) → `anomalies` (detections with metrics) → `narratives` (explanations) + `news_articles` (clustered by anomaly). See `src/database/models.py` for full schema.

**Environment Variables** (`.env`):
```bash
# Database
DATABASE__PASSWORD=yourpass           # PostgreSQL password

# LLM (for Phase 2)
LLM__PROVIDER=anthropic              # openai, anthropic, or ollama
LLM__MODEL=claude-3-5-haiku-20241022 # Model to use
ANTHROPIC_API_KEY=sk-ant-...         # or OPENAI_API_KEY

# Detection thresholds
DETECTION__Z_SCORE_THRESHOLD=3.0     # 3-sigma events
DETECTION__NEWS_WINDOW_MINUTES=30    # News search ±30min

# News sources (required for Phase 1)
NEWS__CRYPTOPANIC_API_KEY=your_key
NEWS__REDDIT_CLIENT_ID=your_id
NEWS__REDDIT_CLIENT_SECRET=your_secret

# Clustering
CLUSTERING__EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers model
CLUSTERING__MIN_CLUSTER_SIZE=2                 # Minimum articles per cluster
```

**Per-Asset Tuning** (`config/thresholds.yaml`):
```yaml
asset_specific_thresholds:
  BTC-USD:
    z_score: 3.5  # Stable assets need higher threshold
  DOGE-USD:
    z_score: 2.5  # Volatile meme coins need lower threshold
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest                                            # All tests
pytest --cov=src --cov-report=html               # With coverage
pytest tests/unit/phase1/test_statistical.py     # Specific file

# Code quality
black .              # Format (line length 100)
ruff check .         # Lint
mypy src/            # Type checking

# Database migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback
```

## Examples

### Detecting Anomalies

```python
import pandas as pd
from src.phase1_detector.anomaly_detection.statistical import AnomalyDetector

prices = pd.DataFrame({
    'timestamp': [...],
    'price': [45000, 45100, 45050, 47000, 45200],  # Spike at index 3
    'volume': [1000, 1100, 1050, 5000, 1200],      # Volume spike
    'symbol': ['BTC-USD'] * 5
})

detector = AnomalyDetector()
anomalies = detector.detect_all(prices)

# Output: Anomaly(type='combined', price_change=4.40%, z_score=3.87, confidence=0.89)
```

### Clustering News Articles

```python
from src.phase1_detector.clustering import NewsClusterer
from src.phase1_detector.news_aggregation import NewsAggregator
from datetime import datetime

# Fetch news around anomaly
aggregator = NewsAggregator()
articles = await aggregator.get_news_for_anomaly(
    symbols=["BTC-USD"],
    anomaly_time=datetime.now(),
    window_minutes=30
)

# Cluster similar articles
clusterer = NewsClusterer()
result = clusterer.cluster_for_anomaly(anomaly_id, articles)

print(f"Found {result['n_clusters']} clusters:")
for cluster_id, indices in result['clusters'].items():
    if cluster_id != -1:  # Skip noise
        print(f"  Cluster {cluster_id}: {len(indices)} articles")
```

## Cost & Performance

**Monthly costs** (20 cryptos, 200 narratives/day): $20-100
- Price & News APIs: Free (Coinbase, CryptoPanic, Reddit)
- LLM (Anthropic Haiku): $20-50
- PostgreSQL: Free (self-hosted) or $25 (managed)

**Optimization**: Use Haiku (10x cheaper than GPT-4) · Cache embeddings · Reduce polling during low volatility

## Contributing

Contributions welcome! Fork → feature branch → PR. **Code standards**: Black (100 chars) · Type hints · Docstrings · Tests required.

## License

MIT License

---

**Philosophy**: *Workflow first, Agent second.* Deterministic detection ensures we never hallucinate market explanations.
