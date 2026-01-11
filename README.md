# Market Anomaly Narrative Engine (MANE)

> **Detects crypto price anomalies using statistical methods and generates AI-powered narratives explaining why they happened.**

## Overview

The Market Anomaly Narrative Engine solves a critical problem in quantitative finance: **dashboards tell you *what* changed, but rarely *why***. Current LLM solutions often hallucinate connections between unrelated events. MANE takes a different approach:

1. **Deterministic Detection** - Statistical algorithms detect real anomalies (no guessing)
2. **Time-Windowed News** - Links anomalies to news within ±30 minutes (causal filtering)
3. **AI Reasoning** - LLM agent with tools investigates and writes narratives
4. **Validation** - Rule-based and LLM judge validates explanations

**Architecture Philosophy**: Workflow first (predictable), Agent second (reasoning)

## Features

- ✅ **Multi-Algorithm Anomaly Detection**
  - Z-Score detector (3-sigma events)
  - Bollinger Bands breakout detection
  - Volume spike detection
  - Combined detector (highest confidence)

- ✅ **Provider-Agnostic LLM Integration**
  - OpenAI GPT-4o
  - Anthropic Claude 3.5 (Haiku/Sonnet)
  - Local models via Ollama

- ✅ **Robust Data Pipeline**
  - PostgreSQL time-series storage
  - SQLAlchemy ORM with migrations
  - Configurable detection thresholds

- 🚧 **News Aggregation** (Coming soon)
  - CryptoPanic API
  - Reddit (r/cryptocurrency)
  - NewsAPI

- 🚧 **Agent Tools** (Coming soon)
  - Timestamp verification (causality)
  - Sentiment analysis (FinBERT)
  - Historical pattern search
  - Market context checking
  - Social sentiment analysis

## Quick Start

### Prerequisites

- Python 3.13+
- uv (https://github.com/astral-sh/uv)
- PostgreSQL 14+ (or Docker)
- API keys for LLM provider (OpenAI or Anthropic)

## Installation

### 1. Clone and navigate to the repository
```bash
git clone https://github.com/your-org/market-anomaly-narrative-engine.git
cd market-anomaly-narrative-engi
```

### 2. **Create virtual environment**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
uv sync
```

4. **Set up PostgreSQL**
```bash
# Option 1: Docker
docker run --name mane-postgres -e POSTGRES_PASSWORD=yourpassword -p 5432:5432 -d postgres:14

# Option 2: Local PostgreSQL
createdb mane_db
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

**Required environment variables**:
```bash
# Database
DATABASE__PASSWORD=yourpassword

# LLM (choose one)
ANTHROPIC_API_KEY=sk-ant-...  # Recommended
# or
OPENAI_API_KEY=sk-...

# News APIs (for full pipeline)
NEWS__CRYPTOPANIC_API_KEY=your_key
NEWS__REDDIT_CLIENT_ID=your_id
NEWS__REDDIT_CLIENT_SECRET=your_secret
```

6. **Initialize database**
```bash
mane init-db
```

### Usage

**Run anomaly detection** (once implemented):
```bash
# Detect anomalies for Bitcoin
mane detect --symbol BTC-USD

# Start scheduled detection (every 60 seconds)
mane serve

# View recent narratives
mane list-narratives --limit 10
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
market-anomaly-narrative-engine/
├── config/
│   ├── settings.py              # Pydantic settings (env vars, thresholds)
│   └── thresholds.yaml          # Per-asset detection tuning
├── src/
│   ├── phase1_detector/         # Statistical detection & news clustering
│   │   ├── data_ingestion/      # Coinbase/Binance price APIs
│   │   ├── anomaly_detection/   # ✅ Z-score, Bollinger, volume detectors
│   │   ├── news_aggregation/    # CryptoPanic, NewsAPI, Reddit
│   │   └── clustering/          # sentence-transformers + HDBSCAN
│   ├── phase2_journalist/       # LLM Agent narrative generation
│   │   ├── agent.py             # LiteLLM orchestrator with tool loop
│   │   └── tools/               # 5 tools: verify_timestamp, sentiment_check, etc.
│   ├── phase3_skeptic/          # Validation engine
│   │   ├── validator.py         # Rule-based + Judge LLM validation
│   │   └── rules.py             # Sentiment matching, magnitude checks
│   ├── database/
│   │   ├── models.py            # ✅ SQLAlchemy ORM (prices, anomalies, narratives)
│   │   └── connection.py        # ✅ PostgreSQL connection pool
│   ├── llm/
│   │   └── client.py            # LiteLLM wrapper
│   └── orchestration/
│       ├── pipeline.py          # Phase 1→2→3 coordinator
│       └── scheduler.py         # APScheduler cron jobs
├── tests/                       # Unit and integration tests
├── main.py                      # CLI entry point (Click)
└── pyproject.toml              # ✅ Dependencies and project config
```

**Legend**: ✅ = Implemented | 🚧 = In Progress | ⏳ = Planned

## Database Schema

### Core Tables

**prices** - Time-series price data
```sql
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price FLOAT NOT NULL,
    volume_24h FLOAT,
    source VARCHAR(20),
    INDEX idx_symbol_timestamp (symbol, timestamp)
);
```

**anomalies** - Detected statistical anomalies
```sql
CREATE TABLE anomalies (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    anomaly_type ENUM('price_spike', 'price_drop', 'volume_spike', 'combined'),
    z_score FLOAT,
    price_change_pct FLOAT,
    confidence FLOAT,
    INDEX idx_symbol_detected (symbol, detected_at)
);
```

**narratives** - Generated explanations
```sql
CREATE TABLE narratives (
    id UUID PRIMARY KEY,
    anomaly_id UUID REFERENCES anomalies(id) UNIQUE,
    narrative_text TEXT NOT NULL,
    validation_passed BOOLEAN,
    llm_provider VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

See `src/database/models.py` for complete schema.

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Database
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__DATABASE=mane_db
DATABASE__USERNAME=postgres
DATABASE__PASSWORD=your_postgres_password

# LLM Provider (choose one: openai, anthropic, ollama)
LLM__PROVIDER=anthropic
LLM__MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Detection Thresholds
DETECTION__Z_SCORE_THRESHOLD=3.0        # 3-sigma events
DETECTION__VOLUME_Z_THRESHOLD=2.5       # Volume spikes
DETECTION__LOOKBACK_WINDOW_MINUTES=60   # Baseline window
DETECTION__NEWS_WINDOW_MINUTES=30       # News search ±30min
```

### Per-Asset Thresholds

Fine-tune detection sensitivity in `config/thresholds.yaml`:

```yaml
asset_specific_thresholds:
  BTC-USD:
    z_score: 3.5  # Bitcoin is more stable
  DOGE-USD:
    z_score: 2.5  # Meme coins more volatile
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/phase1/test_statistical.py
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Implementation Status

### ✅ Completed

- [x] Project structure and configuration
- [x] Database models (SQLAlchemy ORM)
- [x] Settings management (Pydantic)
- [x] Statistical anomaly detectors
  - [x] Z-Score detector
  - [x] Bollinger Bands detector
  - [x] Volume spike detector
  - [x] Combined detector

### 🚧 In Progress

- [ ] Data ingestion (Coinbase API)
- [ ] News aggregation (CryptoPanic, Reddit)
- [ ] News clustering (embeddings + HDBSCAN)

### ⏳ Planned

- [ ] LiteLLM client wrapper
- [ ] Agent tools (5 tools)
- [ ] Journalist agent with tool loop
- [ ] Validation engine (rules + judge LLM)
- [ ] Pipeline orchestrator
- [ ] CLI interface
- [ ] Alembic migrations
- [ ] Unit tests
- [ ] Integration tests

## Example Usage

### Detecting Anomalies with Statistical Detectors

```python
import pandas as pd
from src.phase1_detector.anomaly_detection.statistical import AnomalyDetector

# Sample price data
prices = pd.DataFrame({
    'timestamp': [...],
    'price': [45000, 45100, 45050, 47000, 45200],  # Spike at index 3
    'volume': [1000, 1100, 1050, 5000, 1200],      # Volume spike too
    'symbol': ['BTC-USD'] * 5
})

# Initialize detector
detector = AnomalyDetector()

# Detect anomalies
anomalies = detector.detect_all(prices)

for anomaly in anomalies:
    print(f"Anomaly detected: {anomaly.anomaly_type}")
    print(f"Price change: {anomaly.price_change_pct:.2f}%")
    print(f"Z-score: {anomaly.z_score:.2f}")
    print(f"Confidence: {anomaly.confidence:.2f}")
```

**Output**:
```
Anomaly detected: combined
Price change: 4.40%
Z-score: 3.87
Confidence: 0.89
```

## Cost Estimation

**Monthly costs for MVP** (monitoring 20 cryptos):

| Component | Cost |
|-----------|------|
| Crypto Price APIs | Free (Coinbase/Binance free tier) |
| News APIs | Free (CryptoPanic 2K req/day, Reddit free) |
| LLM (Anthropic Haiku) | ~$20-50/month (200 narratives/day) |
| PostgreSQL | Free (self-hosted) or $25/month (managed) |
| Compute | Free (local) or $24/month (cloud) |
| **Total** | **$20-100/month** |

**Cost optimization**:
- Use Anthropic Claude 3.5 Haiku (10x cheaper than GPT-4)
- Cache news articles and embeddings
- Reduce polling frequency during low volatility

## Troubleshooting

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready

# Check credentials in .env
cat .env | grep DATABASE
```

### Missing dependencies

```bash
# Reinstall all dependencies
pip install -e ".[dev]"
```

### API rate limits

- CryptoPanic: 2000 requests/day (free tier)
- Reddit: Authenticated apps have higher limits
- LLM: Monitor token usage in logs

## Roadmap

### v0.1 (Current)
- ✅ Core statistical detectors
- ✅ Database models
- ✅ Configuration system

### v0.2 (Next)
- 🚧 Price data ingestion
- 🚧 News aggregation
- 🚧 Basic clustering

### v0.3
- LLM agent with tools
- Narrative generation
- Validation engine

### v0.4
- Full pipeline orchestration
- CLI interface
- Scheduled detection

### v1.0
- Production deployment
- Web dashboard
- REST API

## Contributing

Contributions welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Code standards**:
- Black formatting (line length 100)
- Type hints required
- Docstrings for all public functions
- Tests for new features

## License

This project is licensed under the MIT License.

## Acknowledgments

- **Statistical Methods**: Z-score and Bollinger Bands are industry-standard techniques
- **LLM Integration**: Built on LiteLLM for provider-agnostic access
- **Inspiration**: Solving the "why" problem in quantitative dashboards

## Contact

For questions, issues, or feature requests, please open an issue on GitHub.

---

**Built with the philosophy**: *Workflow first, Agent second.* Deterministic detection ensures we never hallucinate market explanations.
