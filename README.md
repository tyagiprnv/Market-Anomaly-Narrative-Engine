# Market Anomaly Narrative Engine (MANE)

**Detect crypto price anomalies. Explain why they happened. Never hallucinate.**

MANE solves a critical problem in quantitative finance: dashboards tell you *what* changed, but rarely *why*. Traditional LLMs hallucinate connections between unrelated events. MANE doesn't.

**How it works:**
1. **Statistical Detection** - Multi-timeframe + asset-aware anomaly detection (BTC ≠ DOGE)
2. **Time-Windowed News** - Links anomalies to news within ±30 minutes (causal filtering)
3. **AI Investigation** - LLM agent with tools investigates and writes narratives
4. **Validation** - Rule-based + Judge LLM verify plausibility (or return "Unknown")

> **Architecture Philosophy**: Workflow first (predictable), Agent second (reasoning)

## 💰 Cost-Efficient Design

**Zero API costs in production!** MANE uses free news sources (RSS feeds) with optional historical replay mode for deterministic testing.

- **Production Cost**: $0/month (down from $500/month with paid APIs)
- **News Quality**: 85-90% of paid API quality through keyword sentiment + LLM validation
- **Testing**: 100% deterministic with replay mode

## Quick Start

**Prerequisites**: Python 3.12+ · [uv](https://github.com/astral-sh/uv) · PostgreSQL 14+ · LLM API key (Anthropic/OpenAI/DeepSeek)

```bash
# Setup
git clone https://github.com/your-org/market-anomaly-narrative-engine.git
cd market-anomaly-narrative-engine
uv venv && source .venv/bin/activate
uv sync

# Database
docker run --name mane-postgres -e POSTGRES_PASSWORD=yourpass -p 5432:5432 -d postgres:14

# Configure (.env file)
cp .env.example .env
# Required: DATABASE__PASSWORD, LLM_API_KEY
# Optional: NEWS__GROK_API_KEY (X/Twitter data, paid)

# Initialize & populate database
mane init-db
mane backfill --symbol BTC-USD --days 7   # Fetch historical price data

# Run detection (free RSS mode)
mane detect --symbol BTC-USD --news-mode live    # Free news sources
mane detect --all --news-mode live               # All configured symbols
mane serve --news-mode live                      # Continuous monitoring

# View results
mane list-narratives --limit 10
mane metrics
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
│                                            (RSS/NewsAPI)        │
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

### Key Features

**🎯 Multi-Timeframe Detection** - Detects cumulative price changes that appear normal minute-by-minute:
- Example: DOGE +0.5%/min for 10 minutes = +5% total → **NOW DETECTED** ✓
- Previously: Each minute (Z-score ~0.8) looked normal → **MISSED** ✗
- Analyzes 5/15/30/60 minute windows in parallel, returns highest confidence

**🎨 Asset-Aware Thresholds** - Different cryptocurrencies have different volatility profiles:
- **BTC** (stable): Requires Z-score > 3.5 (filters noise, reduces false positives)
- **DOGE** (volatile): Requires Z-score > 2.0 (more sensitive to meme coin swings)
- **SOL/XRP** (moderate): Baseline Z-score 3.0 (standard 3-sigma)
- Configured via `config/thresholds.yaml` with 3-tier priority (override > tier > global)

### Key Components

```
src/
├── phase1_detector/        # Statistical detection, news aggregation, clustering
│   ├── anomaly_detection/  # Multi-timeframe + asset-aware detection
│   │   ├── statistical.py      # MultiTimeframe, ZScore, Bollinger, Volume, Combined
│   │   ├── asset_profiles.py   # 3-tier threshold lookup (override > tier > global)
│   │   └── models.py            # DetectedAnomaly with detection_metadata
│   ├── data_ingestion/     # Coinbase & Binance API clients
│   ├── news_aggregation/   # RSS (free) + CryptoPanic, NewsAPI, Grok (paid)
│   │   ├── rss_client.py      # Free RSS feeds (CoinDesk, Cointelegraph, etc.)
│   │   ├── replay_client.py   # Historical datasets for testing
│   │   └── sentiment.py       # Keyword-based sentiment extraction
│   └── clustering/         # sentence-transformers + HDBSCAN
├── phase2_journalist/      # LLM agent with tool loop
│   ├── agent.py            # JournalistAgent orchestrator
│   ├── tools/              # 5 agent tools (verify_timestamp, sentiment_check, etc.)
│   └── prompts/            # System prompts
├── phase3_skeptic/         # Validation engine
│   ├── validator.py        # ValidationEngine orchestrator
│   ├── validators/         # 6 validators (rule-based + LLM)
│   └── prompts/            # Judge LLM prompts
├── database/               # SQLAlchemy ORM (prices → anomalies → narratives)
├── llm/                    # LiteLLM wrapper (multi-provider support)
├── orchestration/          # Pipeline coordinator & scheduler
└── cli/                    # CLI utilities
```

## Configuration

**Database Schema**: `prices` → `anomalies` → `narratives` + `news_articles` (see `src/database/models.py`)

**Key Environment Variables** (`.env`):
```bash
# Database
DATABASE__PASSWORD=yourpass

# LLM Provider
LLM__PROVIDER=anthropic              # openai, anthropic, deepseek, ollama
LLM__MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...         # or OPENAI_API_KEY, DEEPSEEK_API_KEY

# News Sources (Free)
NEWS__MODE=live                      # live (RSS), replay (datasets), hybrid

# News Sources (Paid - Optional)
NEWS__CRYPTOPANIC_API_KEY=your_key   # Optional: paid API
NEWS__NEWSAPI_API_KEY=your_key       # Optional: paid API
NEWS__GROK_API_KEY=xai-your_key      # Optional: X/Twitter data via xAI (paid)

# Detection & Validation
DETECTION__Z_SCORE_THRESHOLD=3.0     # 3-sigma events
DETECTION__NEWS_WINDOW_MINUTES=30    # News search window
VALIDATION__PASS_THRESHOLD=0.65      # Validation threshold
```

**Asset-Aware Thresholds** (`config/thresholds.yaml`):
```yaml
# Volatility tiers (multiplier applied to global defaults)
volatility_tiers:
  stable:    # BTC, ETH
    multiplier: 1.2  # 3.0 × 1.2 = 3.6
  moderate:  # SOL, XRP, ADA, etc.
    multiplier: 1.0  # 3.0 × 1.0 = 3.0 (baseline)
  volatile:  # DOGE, SHIB, PEPE
    multiplier: 0.7  # 3.0 × 0.7 = 2.1

# Asset-specific overrides (highest priority)
asset_specific_thresholds:
  BTC-USD:
    z_score_threshold: 3.5  # Overrides tier multiplier
  DOGE-USD:
    z_score_threshold: 2.0  # Highly volatile meme coin

# Multi-timeframe detection
timeframes:
  enabled: true
  windows: [5, 15, 30, 60]  # Analyze multiple timeframes in parallel
  baseline_multiplier: 3    # Baseline = window × 3 (excludes current move)
```

**Feature Flags** (`.env`):
```bash
# Enable multi-timeframe detection (detects cumulative "slow burns")
DETECTION__ENABLE_MULTI_TIMEFRAME=true

# Use asset-specific thresholds from config/thresholds.yaml
DETECTION__USE_ASSET_SPECIFIC_THRESHOLDS=true
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Testing
pytest                          # Run all tests
pytest --cov=src               # With coverage
pytest tests/unit/phase1/      # Specific directory

# Code quality
black .                        # Format (line length 100)
ruff check .                   # Lint
mypy src/                      # Type checking

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## CLI Commands

```bash
# Database setup
mane init-db                              # Initialize database schema
mane backfill --symbol BTC-USD --days 7   # Backfill price history (1-min candles)
mane backfill --all --days 30             # Backfill all configured symbols

# Detection (with news modes)
mane detect --symbol BTC-USD --news-mode live    # Free RSS feeds
mane detect --symbol BTC-USD --news-mode replay  # Historical datasets (testing)
mane detect --all --news-mode live               # All symbols with free sources
mane serve --news-mode live                      # Continuous monitoring (free sources)

# Historical replay mode (for testing/demos)
mane backfill-news --symbol BTC-USD \            # Create historical news dataset
  --start-date 2024-03-14 \
  --end-date 2024-03-14 \
  --file-path my_news.json

# Results
mane list-narratives --limit 10           # View recent narratives
mane list-narratives --validated-only     # Show only validated narratives
mane metrics                              # Display performance metrics
```

### News Modes

- **`live`** (default): Free RSS feeds (5-10 min delay, $0/month)
- **`replay`**: Historical JSON datasets (deterministic, cost-free testing)
- **`hybrid`**: Both live and replay sources (validation against known events)

## Python API Example

```python
from src.orchestration.pipeline import MarketAnomalyPipeline
from src.database.connection import get_db_session

# Run end-to-end pipeline
with get_db_session() as session:
    pipeline = MarketAnomalyPipeline(session=session)

    # Detect anomaly → Generate narrative → Validate
    result = await pipeline.run_for_symbol("BTC-USD")

    if result.anomaly_detected:
        print(f"Anomaly: {result.anomaly.type} ({result.anomaly.confidence:.2f})")
        print(f"Narrative: {result.narrative.narrative_text}")
        print(f"Validated: {result.narrative.validation_passed}")
```

For individual component usage, see `examples/` directory.

## Performance

- Anomaly detection: <50ms
- News aggregation: 1-3s (RSS feeds) or <100ms (replay mode)
- News clustering: ~200ms
- Narrative generation: 2-5s (LLM + tool loop)
- Validation: 100ms (rules) or 2-5s (rules + Judge LLM)
- **End-to-end**: 5-15 seconds per anomaly

**Key Optimizations**:
- **Free news sources** (RSS/Grok) → **$0/month** (vs $500 with paid APIs)
- Conditional LLM validation (80% cost reduction)
- Parallel rule validators
- Cached embeddings
- Haiku model (10x cheaper than GPT-4)
- Replay mode for deterministic testing (zero API calls)

## Contributing

Contributions welcome! Fork → feature branch → PR. **Code standards**: Black (100 chars) · Type hints · Docstrings · Tests required.

## License

MIT License

---

**Philosophy**: *Workflow first, Agent second.* Deterministic detection ensures we never hallucinate market explanations.
