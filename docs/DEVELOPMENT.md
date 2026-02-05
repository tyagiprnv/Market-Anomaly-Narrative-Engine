# Development Guide

## Getting Started

### Prerequisites

Ensure you have:
- Python 3.12+ (`python --version`) - Tested with Python 3.12.8 and 3.13
- Node.js 18+ (`node --version`) - For web interface
- PostgreSQL 14+ (`psql --version`)
- pip or uv package manager (`pip --version` or `uv --version`)
- npm or pnpm (`npm --version`) - For web interface
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

6. **Initialize database**
```bash
# Create tables
mane init-db

# Verify database is ready
psql -U postgres -d mane_db -c "\dt"
```

7. **Setup web interface** (optional)
```bash
# Backend
cd web/backend
npm install
npx prisma generate    # Generate Prisma client from existing DB

# Create .env file
echo 'DATABASE_URL="postgresql://postgres:devpassword@localhost:5432/mane_db"' > .env
echo 'JWT_SECRET="dev-secret-change-in-production"' >> .env
echo 'NODE_ENV="development"' >> .env

# Start backend server (port 3001)
npm run dev

# Frontend (new terminal)
cd web/frontend
npm install

# Start frontend server (port 5173)
npm run dev
```

## Project Structure

```
market-anomaly-narrative-engine/
├── config/                  # Configuration files
│   ├── settings.py          # Pydantic settings loader
│   └── thresholds.yaml      # Per-asset detection thresholds
├── src/                     # Python source code
│   ├── phase1_detector/     # ✅ Statistical detection + data ingestion + news
│   ├── phase2_journalist/   # ✅ LLM agent with tool loop
│   ├── phase3_skeptic/      # ✅ Validation engine (6 validators)
│   ├── database/            # ✅ ORM models
│   ├── llm/                 # ✅ LiteLLM wrapper
│   ├── orchestration/       # ✅ Pipeline + scheduler
│   └── cli/                 # ✅ CLI utilities
├── web/                     # ✅ Full-stack web interface
│   ├── backend/             # Express + TypeScript + Prisma
│   │   ├── src/             # API routes and middleware
│   │   ├── prisma/          # Prisma schema (introspected)
│   │   └── package.json     # Node dependencies
│   ├── frontend/            # React + TypeScript + Vite
│   │   ├── src/             # React components
│   │   ├── public/          # Static assets
│   │   └── package.json     # Node dependencies
│   └── shared/              # Shared TypeScript types
├── tests/                   # Python test suite (216 tests)
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── fixtures/            # Test data
├── docs/                    # Documentation
├── main.py                  # Python CLI entry point
└── pyproject.toml           # Python dependencies
```

## Development Workflow

### Working with Python Backend

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit code in `src/` directory (Python backend).

### 3. Run Tests

```bash
# Run all tests (165+ tests)
pytest

# Run specific test file
pytest tests/unit/phase1/test_statistical.py

# Run orchestration tests
pytest tests/unit/orchestration/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report

# Run specific test by name
pytest -k "test_pipeline_success"
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

---

### Working with Web Interface

### 1. Backend Development (Express + TypeScript)

```bash
cd web/backend

# Start development server with hot reload
npm run dev

# Watch mode for TypeScript compilation
npm run dev
```

**Making Changes**:
1. Edit routes in `src/routes/`
2. Add middleware in `src/middleware/`
3. Update Prisma schema if needed:
   ```bash
   # If Python schema changed, re-introspect
   npx prisma db pull
   npx prisma generate
   ```
4. Add tests in `tests/`
5. Run tests: `npm test`

**File Structure**:
```
web/backend/src/
├── index.ts              # Express app entry point
├── routes/
│   ├── auth.routes.ts        # Authentication endpoints
│   ├── anomaly.routes.ts     # Anomaly CRUD
│   ├── news.routes.ts        # News endpoints
│   └── ...
├── middleware/
│   ├── auth.middleware.ts    # JWT verification
│   ├── rateLimiter.middleware.ts  # Rate limiting
│   └── error.middleware.ts   # Error handling
└── lib/
    ├── prisma.ts         # Prisma client singleton
    ├── jwt.ts            # JWT utilities
    └── logger.ts         # Winston logger
```

### 2. Frontend Development (React + TypeScript)

```bash
cd web/frontend

# Start development server with hot reload
npm run dev
# Opens http://localhost:5173
```

**Making Changes**:
1. Edit pages in `src/pages/`
2. Add components in `src/components/`
3. Create hooks in `src/hooks/`
4. Update API client in `src/lib/api.ts`
5. Add tests in `src/__tests__/`
6. Run tests: `npm test`

**File Structure**:
```
web/frontend/src/
├── main.tsx              # Entry point
├── App.tsx               # Root component with routing
├── pages/
│   ├── Dashboard.tsx         # Live anomaly feed
│   ├── AnomalyDetail.tsx     # Detail view
│   ├── ChartView.tsx         # Price charts
│   └── HistoricalBrowser.tsx # Archive browser
├── components/
│   ├── dashboard/
│   ├── charts/
│   └── common/
├── hooks/
│   ├── useAnomalies.ts   # TanStack Query hooks
│   └── useAuth.ts        # Authentication
└── lib/
    ├── api.ts            # API client
    └── types.ts          # TypeScript types
```

### 3. Debugging Web Interface

**Backend Debugging**:
```bash
cd web/backend

# With Node debugger
node --inspect dist/index.js

# Or with ts-node
npm run dev:debug

# Connect with Chrome DevTools or VS Code debugger
```

**Frontend Debugging**:
- Use React DevTools browser extension
- Use browser console (Network tab for API calls)
- Check TanStack Query DevTools (enabled in dev mode)

**Common Issues**:
1. **CORS errors**: Check `cors()` configuration in `backend/src/index.ts`
2. **401 Unauthorized**: Check JWT token in cookies (use browser DevTools)
3. **Prisma client not generated**: Run `npx prisma generate`
4. **Port conflicts**: Change `PORT` in backend `.env` or frontend `vite.config.ts`

### 4. Database Changes

When modifying Python database models:

```bash
# 1. Update src/database/models.py (Python)

# 2. Generate Alembic migration (future)
alembic revision --autogenerate -m "Add new column"
alembic upgrade head

# 3. Re-introspect with Prisma
cd web/backend
npx prisma db pull      # Pull updated schema
npx prisma generate     # Regenerate TypeScript types

# 4. Update TypeScript types if needed
# Edit web/shared/types.ts
```

---

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
target-version = ['py312']
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
target-version = "py312"
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

### Python Development Environment

```bash
# .env for Python backend
DATABASE__PASSWORD=devpassword
LLM__PROVIDER=ollama
LLM__MODEL=llama3.2:3b
LOG_LEVEL=DEBUG
DETECTION__ENABLE_MULTI_TIMEFRAME=true
ORCHESTRATION__PRICE_HISTORY_LOOKBACK_MINUTES=240  # CRITICAL!
```

### Web Backend Development Environment

```bash
# web/backend/.env
DATABASE_URL="postgresql://postgres:devpassword@localhost:5432/mane_db"
JWT_SECRET="dev-secret-change-in-production"
NODE_ENV="development"
CORS_ORIGIN="http://localhost:5173"
PORT=3001
```

### Web Frontend Development Environment

```bash
# web/frontend/.env (optional)
VITE_API_URL="http://localhost:3001"
```

### Testing Environment

```bash
# Python tests - use in-memory SQLite
DATABASE__URL=sqlite:///:memory:

# Web backend tests
DATABASE_URL="postgresql://postgres:testpass@localhost:5432/mane_test_db"
NODE_ENV="test"
```

### Production Environment

```bash
# Python backend
export DATABASE__PASSWORD=<secret>
export ANTHROPIC_API_KEY=<secret>
export LOG_LEVEL=INFO

# Web backend
export DATABASE_URL="postgresql://user:pass@prod-host:5432/mane_db?sslmode=require"
export JWT_SECRET=<strong-random-secret>
export NODE_ENV="production"
export CORS_ORIGIN="https://yourdomain.com"
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
