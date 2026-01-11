# Development Guide

## Getting Started

### Prerequisites

Ensure you have:
- Python 3.13+ (`python --version`)
- PostgreSQL 14+ (`psql --version`)
- pip (`pip --version`)
- Git

### Initial Setup

1. **Clone repository**
```bash
git clone <repository-url>
cd market-anomaly-narrative-engine
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
# Production dependencies
pip install -e .

# Development dependencies (includes testing, linting)
pip install -e ".[dev]"
```

4. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

5. **Start PostgreSQL**
```bash
# Option 1: Docker (recommended for development)
docker run --name mane-postgres \
  -e POSTGRES_PASSWORD=devpassword \
  -p 5432:5432 \
  -d postgres:14

# Option 2: Local PostgreSQL
createdb mane_db
```

6. **Initialize database** (once implemented)
```bash
mane init-db
```

## Project Structure

```
market-anomaly-narrative-engine/
├── config/                  # Configuration files
│   ├── settings.py          # Pydantic settings loader
│   └── thresholds.yaml      # Per-asset detection thresholds
├── src/                     # Source code
│   ├── phase1_detector/     # ✅ Statistical detection
│   ├── phase2_journalist/   # 🚧 LLM agent
│   ├── phase3_skeptic/      # 🚧 Validation
│   ├── database/            # ✅ ORM models
│   ├── llm/                 # 🚧 LiteLLM wrapper
│   └── orchestration/       # 🚧 Pipeline
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test data
├── docs/                    # Documentation
├── main.py                  # CLI entry point
└── pyproject.toml           # Dependencies
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit code in `src/` directory.

### 3. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/phase1/test_statistical.py

# Run with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

### 4. Code Quality Checks

```bash
# Format code (auto-fixes)
black .

# Lint (checks for issues)
ruff check .

# Type checking
mypy src/
```

### 5. Commit Changes

```bash
git add .
git commit -m "Add feature: your feature description"
```

**Commit Message Guidelines**:
- Use imperative mood ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Add detailed description in body if needed

Example:
```
Add Z-score anomaly detector

- Implements 3-sigma detection algorithm
- Configurable threshold via settings
- Returns DetectedAnomaly model
- Includes unit tests
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
# Open Pull Request on GitHub
```

## Testing Strategy

### Unit Tests

Test individual functions/classes in isolation.

**Location**: `tests/unit/`

**Example**: Testing Z-score detector

```python
# tests/unit/phase1/test_statistical.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.phase1_detector.anomaly_detection.statistical import ZScoreDetector

def test_zscore_detects_spike():
    """Test that Z-score detector identifies price spike."""
    # Arrange: Create sample data with spike
    prices = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(10, 0, -1)],
        'price': [100, 101, 100.5, 102, 101.5, 110, 102, 101, 100.5, 100],  # Spike at index 5
        'volume': [1000] * 10,
        'symbol': ['BTC-USD'] * 10
    })

    detector = ZScoreDetector(threshold=3.0, window_minutes=10)

    # Act: Run detector
    anomalies = detector.detect(prices)

    # Assert: Anomaly detected
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == 'price_spike'
    assert anomalies[0].z_score > 3.0

def test_zscore_no_anomaly_on_normal_data():
    """Test that normal price movements don't trigger detection."""
    prices = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(10, 0, -1)],
        'price': [100 + i * 0.1 for i in range(10)],  # Gradual increase
        'volume': [1000] * 10,
        'symbol': ['BTC-USD'] * 10
    })

    detector = ZScoreDetector(threshold=3.0, window_minutes=10)
    anomalies = detector.detect(prices)

    assert len(anomalies) == 0
```

**Run unit tests**:
```bash
pytest tests/unit/ -v
```

### Integration Tests

Test multiple components working together.

**Location**: `tests/integration/`

**Example**: End-to-end pipeline test

```python
# tests/integration/test_pipeline.py
import pytest
from datetime import datetime, timedelta
from src.orchestration.pipeline import AnomalyPipeline

@pytest.mark.integration
async def test_full_pipeline(test_db):
    """Test complete anomaly detection pipeline."""
    # 1. Inject mock price data
    # 2. Run detector
    # 3. Verify anomaly saved to DB
    # 4. Verify news fetched
    # 5. Verify narrative generated
    pass  # Implementation pending
```

**Run integration tests**:
```bash
pytest tests/integration/ -v --asyncio-mode=auto
```

### Test Fixtures

Reusable test data in `tests/fixtures/`

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from src.database.models import Base

@pytest.fixture(scope="session")
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def sample_btc_prices():
    """Return sample BTC price data."""
    return pd.DataFrame({...})
```

## Code Style

### Black Formatting

**Configuration** (in `pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py313']
```

**Usage**:
```bash
black .                  # Format all files
black src/database/      # Format specific directory
black --check .          # Check without modifying
```

### Ruff Linting

**Configuration** (in `pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py313"
```

**Usage**:
```bash
ruff check .             # Lint all files
ruff check --fix .       # Auto-fix issues
```

### Type Hints

All functions should have type hints:

```python
from typing import List, Optional
from datetime import datetime

def detect_anomalies(
    prices: pd.DataFrame,
    threshold: float = 3.0,
    current_time: Optional[datetime] = None
) -> List[DetectedAnomaly]:
    """Detect anomalies in price data.

    Args:
        prices: DataFrame with columns [timestamp, price, volume]
        threshold: Z-score threshold for detection
        current_time: Time to check (default: latest)

    Returns:
        List of detected anomalies
    """
    pass
```

**Check types**:
```bash
mypy src/
```

## Debugging

### Using Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() in Python 3.7+
breakpoint()
```

### Logging

Use `structlog` for structured logging:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "anomaly_detected",
    symbol="BTC-USD",
    z_score=3.5,
    price_change_pct=-5.2
)
```

**Output** (JSON format):
```json
{
  "event": "anomaly_detected",
  "symbol": "BTC-USD",
  "z_score": 3.5,
  "price_change_pct": -5.2,
  "timestamp": "2024-01-15T14:15:00.123Z",
  "level": "info"
}
```

### Database Debugging

**View current connections**:
```sql
SELECT * FROM pg_stat_activity WHERE datname = 'mane_db';
```

**Check table sizes**:
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Common Development Tasks

### Adding a New Detector

1. Create detector class in `src/phase1_detector/anomaly_detection/`
2. Inherit from base or implement standard interface
3. Add to `AnomalyDetector.detect_all()` method
4. Write unit tests in `tests/unit/phase1/`
5. Update documentation

**Example**:
```python
# src/phase1_detector/anomaly_detection/statistical.py
class RSIDetector:
    """Detect overbought/oversold using RSI indicator."""

    def __init__(self, period: int = 14, threshold_high: float = 70, threshold_low: float = 30):
        self.period = period
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low

    def detect(self, prices: pd.DataFrame) -> List[DetectedAnomaly]:
        # Calculate RSI
        # Check thresholds
        # Return anomalies
        pass
```

### Adding a New Agent Tool

1. Create tool file in `src/phase2_journalist/tools/`
2. Implement `AgentTool` interface
3. Add tool to journalist agent's tool list
4. Write unit tests
5. Update tool documentation

**Example**:
```python
# src/phase2_journalist/tools/check_whale_activity.py
from .base import AgentTool

class CheckWhaleActivityTool(AgentTool):
    name = "check_whale_activity"
    description = "Check for large wallet movements (whale activity)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"}
            },
            "required": ["symbol", "timestamp"]
        }

    async def execute(self, symbol: str, timestamp: str) -> dict:
        # Query on-chain data
        # Detect large transfers
        return {"whale_activity": True, "transfers": [...]}
```

### Modifying Database Schema

1. Update models in `src/database/models.py`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. Update tests

## Performance Profiling

### Using cProfile

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
detector.detect_all(prices)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 slowest functions
```

### Memory Profiling

```bash
pip install memory_profiler

# Add @profile decorator to functions
python -m memory_profiler script.py
```

## Environment Management

### Development Environment

```bash
# .env for development
DATABASE__PASSWORD=devpassword
LLM__PROVIDER=ollama
LLM__MODEL=llama3.2:3b
LOG_LEVEL=DEBUG
```

### Testing Environment

```bash
# Use in-memory SQLite for fast tests
DATABASE__URL=sqlite:///:memory:
```

### Production Environment

```bash
# Use environment variables in production
export DATABASE__PASSWORD=<secret>
export ANTHROPIC_API_KEY=<secret>
export LOG_LEVEL=INFO
```

## Continuous Integration (Future)

### GitHub Actions Example

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src
      - run: black --check .
      - run: ruff check .
```

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed in editable mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

### Database Migration Errors

```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head

# Or drop and recreate
dropdb mane_db
createdb mane_db
alembic upgrade head
```

### Dependency Conflicts

```bash
# Clear cache and reinstall
pip cache purge
pip uninstall -y -r <(pip freeze)
pip install -e ".[dev]"
```

## Resources

- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **LiteLLM Docs**: https://docs.litellm.ai/
- **Pandas Docs**: https://pandas.pydata.org/docs/
- **pytest Docs**: https://docs.pytest.org/

## Getting Help

1. Check existing documentation
2. Search issues on GitHub
3. Ask in discussions
4. Open a new issue with:
   - Python version
   - Error message
   - Steps to reproduce

---

**Happy coding!** Remember: Workflow first, Agent second.
