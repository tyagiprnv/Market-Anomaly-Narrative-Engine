# Market Anomaly Narrative Engine (MANE)

**Detect crypto price anomalies. Explain why they happened. Never hallucinate.**

MANE solves a critical problem in quantitative finance: dashboards tell you *what* changed, but rarely *why*. Traditional LLMs hallucinate connections between unrelated events. MANE doesn't.

**How it works:**
1. **Statistical Detection** - Z-score, Bollinger Bands, volume spikes (deterministic)
2. **Time-Windowed News** - Links anomalies to news within ±30 minutes (causal filtering)
3. **AI Investigation** - LLM agent with tools investigates and writes narratives
4. **Validation** - Rule-based + Judge LLM verify plausibility (or return "Unknown")

> **Architecture Philosophy**: Workflow first (predictable), Agent second (reasoning)

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
# Edit with: DATABASE__PASSWORD, ANTHROPIC_API_KEY, NEWS__CRYPTOPANIC_API_KEY, etc.

# Initialize & populate database
mane init-db
mane backfill --symbol BTC-USD --days 7   # Fetch historical price data

# Run detection
mane detect --symbol BTC-USD              # Single symbol
mane detect --all                         # All configured symbols
mane serve                                # Continuous monitoring

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

### Key Components

```
src/
├── phase1_detector/        # Statistical detection, news aggregation, clustering
│   ├── anomaly_detection/  # Z-score, Bollinger, volume, combined detectors
│   ├── data_ingestion/     # Coinbase & Binance API clients
│   ├── news_aggregation/   # CryptoPanic, Reddit, NewsAPI
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

# News Sources
NEWS__CRYPTOPANIC_API_KEY=your_key
NEWS__REDDIT_CLIENT_ID=your_id
NEWS__REDDIT_CLIENT_SECRET=your_secret

# Detection & Validation
DETECTION__Z_SCORE_THRESHOLD=3.0     # 3-sigma events
DETECTION__NEWS_WINDOW_MINUTES=30    # News search window
VALIDATION__PASS_THRESHOLD=0.65      # Validation threshold
```

**Per-Asset Tuning** (`config/thresholds.yaml`):
```yaml
asset_specific_thresholds:
  BTC-USD:
    z_score: 3.5  # Higher threshold for stable assets
  DOGE-USD:
    z_score: 2.5  # Lower threshold for volatile assets
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

# Detection
mane detect --symbol BTC-USD              # Detect anomalies for single symbol
mane detect --all                         # Detect for all symbols
mane serve                                # Start continuous monitoring scheduler

# Results
mane list-narratives --limit 10           # View recent narratives
mane list-narratives --validated-only     # Show only validated narratives
mane metrics                              # Display performance metrics
```

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

## Cost & Performance

**Monthly costs** (20 cryptos, 200 narratives/day): $20-100
- APIs: Free (Coinbase, CryptoPanic, Reddit)
- LLM: $30-60 (Anthropic Haiku recommended for cost efficiency)
- PostgreSQL: Free (self-hosted) or $25 (managed)

**Performance**:
- Anomaly detection: <50ms
- News clustering: ~200ms
- Narrative generation: 2-5s (LLM + tool loop)
- Validation: 100ms (rules) or 2-5s (rules + Judge LLM)
- **End-to-end**: 5-15 seconds per anomaly

**Key Optimizations**: Conditional LLM validation (80% cost reduction) · Parallel rule validators · Cached embeddings · Haiku model (10x cheaper than GPT-4)

## Contributing

Contributions welcome! Fork → feature branch → PR. **Code standards**: Black (100 chars) · Type hints · Docstrings · Tests required.

## License

MIT License

---

**Philosophy**: *Workflow first, Agent second.* Deterministic detection ensures we never hallucinate market explanations.
