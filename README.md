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

**✅ Phase 2 Complete**: LLM client (LiteLLM wrapper) · Agent tools (5 tools: verify_timestamp, sentiment_check, search_historical, market_context, social_sentiment) · Journalist agent with tool loop · Narrative generation with metadata tracking

**✅ Phase 3 Complete**: Validation engine with 6 validators (5 rule-based + 1 LLM) · Weighted score aggregation · Parallel execution · Conditional LLM validation · Database persistence

**⏳ Next**: Pipeline orchestrator (Phase 1→2→3) · CLI interface · Scheduler · Integration tests

**Progress**: 13/17 components complete (76.5%) · 143 tests passing (100% pass rate)

## Quick Start

**Prerequisites**: Python 3.12+ · [uv](https://github.com/astral-sh/uv) · PostgreSQL 14+ · LLM API key (Anthropic/OpenAI/DeepSeek)

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

### Phase 3: Validation Architecture

**Hybrid Validation** (Rule-based + LLM):
1. **Rule Validators** (parallel execution, ~100ms):
   - `SentimentMatchValidator` - Sentiment aligns with price direction
   - `TimingCoherenceValidator` - News preceded anomaly (causal)
   - `MagnitudeCoherenceValidator` - Language matches z-score magnitude
   - `ToolConsistencyValidator` - Tool results are consistent
   - `NarrativeQualityValidator` - Format, hedging, "Unknown" detection

2. **Judge LLM Validator** (conditional, 2-5s):
   - Only called if rule validators pass threshold (0.5 default)
   - Assesses plausibility, causality, coherence (1-5 scale)
   - Saves 80% of LLM calls by skipping obvious failures

3. **Weighted Aggregation**:
   - Each validator has configurable weight (timing: 1.5, sentiment: 1.2, etc.)
   - Confidence-weighted scoring
   - Pass threshold: 0.65 (configurable)
   - Critical validator override (timing/sentiment failures → reject)

**Result**: `validated=True` + `validation_passed=True/False` + `validation_reason` → Database

### Directory Structure

```
src/
├── phase1_detector/        # ✅ Statistical detection, news aggregation, clustering
│   ├── anomaly_detection/  # ✅ Z-score, Bollinger, volume, combined detectors
│   ├── data_ingestion/     # ✅ Coinbase & Binance API clients
│   ├── news_aggregation/   # ✅ CryptoPanic, Reddit, NewsAPI clients
│   └── clustering/         # ✅ sentence-transformers + HDBSCAN
├── phase2_journalist/      # ✅ LLM agent with 5 tools + narrative generation
│   ├── agent.py            # ✅ JournalistAgent with tool loop orchestration
│   ├── tools/              # ✅ 5 agent tools (verify_timestamp, sentiment_check, etc.)
│   └── prompts/            # ✅ System prompts and context templates
├── phase3_skeptic/         # ✅ Validation engine (rule-based + Judge LLM)
│   ├── validator.py        # ✅ ValidationEngine orchestrator
│   ├── validators/         # ✅ 6 validators (sentiment, timing, magnitude, tools, quality, LLM)
│   └── prompts/            # ✅ Judge LLM system prompt and context templates
├── database/               # ✅ SQLAlchemy ORM (prices → anomalies → narratives)
├── llm/                    # ✅ LiteLLM wrapper (OpenAI, Anthropic, DeepSeek, Ollama)
└── orchestration/          # ⏳ Pipeline coordinator & scheduler
```

## Configuration

**Database Schema**: `prices` (time-series data) → `anomalies` (detections with metrics) → `narratives` (explanations) + `news_articles` (clustered by anomaly). See `src/database/models.py` for full schema.

**Environment Variables** (`.env`):
```bash
# Database
DATABASE__PASSWORD=yourpass           # PostgreSQL password

# LLM (Phase 2 complete)
LLM__PROVIDER=anthropic              # openai, anthropic, deepseek, or ollama
LLM__MODEL=claude-3-5-haiku-20241022 # Model to use
ANTHROPIC_API_KEY=sk-ant-...         # or OPENAI_API_KEY, DEEPSEEK_API_KEY

# Detection thresholds
DETECTION__Z_SCORE_THRESHOLD=3.0     # 3-sigma events
DETECTION__NEWS_WINDOW_MINUTES=30    # News search ±30min

# News sources (Phase 1 complete)
NEWS__CRYPTOPANIC_API_KEY=your_key
NEWS__REDDIT_CLIENT_ID=your_id
NEWS__REDDIT_CLIENT_SECRET=your_secret
NEWS__NEWSAPI_API_KEY=your_key       # Optional third source

# Clustering
CLUSTERING__EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers model
CLUSTERING__MIN_CLUSTER_SIZE=2                 # Minimum articles per cluster

# Validation (Phase 3 complete)
VALIDATION__PASS_THRESHOLD=0.65               # Overall pass threshold
VALIDATION__JUDGE_LLM_ENABLED=true            # Enable LLM validator
VALIDATION__PARALLEL_VALIDATION=true          # Run rule validators in parallel
VALIDATION__SENTIMENT_MATCH_WEIGHT=1.2        # Validator weights (higher = more important)
VALIDATION__TIMING_COHERENCE_WEIGHT=1.5       # Timing is most critical
VALIDATION__JUDGE_LLM_MIN_TRIGGER_SCORE=0.5   # Only call LLM if rules pass this
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

# Run tests (143 tests, 100% pass rate)
pytest                                            # All tests
pytest --cov=src --cov-report=html               # With coverage
pytest tests/unit/phase3/                        # Phase 3 tests (43 tests)
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

### Generating Narratives with AI

```python
from src.phase2_journalist import JournalistAgent
from src.database.connection import get_db_session

# Generate AI-powered narrative for an anomaly
with get_db_session() as session:
    agent = JournalistAgent(session=session)

    # Agent automatically uses tools to investigate
    narrative = await agent.generate_narrative(anomaly, news_articles)

    print(narrative.narrative_text)
    # Output: "Bitcoin dropped 5.2% following SEC announcement of stricter
    # cryptocurrency regulations. The negative sentiment across social media
    # amplified the sell-off."

    print(f"Tools used: {narrative.tools_used}")
    # ['verify_timestamp', 'sentiment_check', 'check_social_sentiment']

    print(f"Confidence: {narrative.confidence_score:.2f}")
    print(f"Generation time: {narrative.generation_time_seconds:.2f}s")
```

### Validating Narratives

```python
from src.phase3_skeptic import ValidationEngine
from src.database.connection import get_db_session

# Validate a narrative with rule-based + LLM validation
with get_db_session() as session:
    engine = ValidationEngine(session=session)

    # Runs 5 rule validators in parallel (~100ms)
    # Then conditionally runs Judge LLM if rules pass threshold
    result = await engine.validate_narrative(narrative)

    if result.validation_passed:
        print(f"✅ Narrative validated (score: {result.aggregate_score:.2f})")
        print(f"   Reason: {result.validation_reason}")
    else:
        print(f"❌ Validation failed (score: {result.aggregate_score:.2f})")
        print(f"   Reason: {result.validation_reason}")

    # Inspect individual validator results
    for name, output in result.validator_results.items():
        if output.success:
            print(f"   {name}: {'✓' if output.passed else '✗'} (score: {output.score:.2f})")
            print(f"      {output.reasoning}")

    # Output example:
    # ✅ Narrative validated (score: 0.78)
    #    Reason: Validation passed (score: 0.78, threshold: 0.65)
    #    sentiment_match: ✓ (score: 1.00)
    #       Positive sentiment (0.75) aligns with price spike
    #    timing_coherence: ✓ (score: 0.90)
    #       3/4 articles are pre-event (75.0%) - strong causal coherence
    #    judge_llm: ✓ (score: 0.83)
    #       Strong causal link with good timing (plausibility: 4, causality: 5, coherence: 4)
```

## Cost & Performance

**Monthly costs** (20 cryptos, 200 narratives/day): $20-100
- Price & News APIs: Free (Coinbase, CryptoPanic, Reddit)
- LLM costs (Anthropic Haiku):
  - Narrative generation: $20-40/month (~200 narratives/day)
  - Validation (Judge LLM): $10-20/month (~80% skip via conditional execution)
- PostgreSQL: Free (self-hosted) or $25 (managed)

**Performance**:
- Anomaly detection: <50ms (deterministic)
- News clustering: ~200ms (embeddings + HDBSCAN)
- Narrative generation: 2-5 seconds (LLM + tools)
- Validation: 100ms (rules only) or 2-5s (rules + Judge LLM)
- **End-to-end pipeline**: 5-15 seconds per anomaly

**Optimization**: Use Haiku (10x cheaper than GPT-4) · Cache embeddings · Parallel validators (~5x speedup) · Conditional LLM (saves 80% of validation calls) · Reduce polling during low volatility

## Contributing

Contributions welcome! Fork → feature branch → PR. **Code standards**: Black (100 chars) · Type hints · Docstrings · Tests required.

## License

MIT License

---

**Philosophy**: *Workflow first, Agent second.* Deterministic detection ensures we never hallucinate market explanations.
