# Testing Guide

## Overview

Comprehensive testing guide for Market Anomaly Narrative Engine covering:
- Unit tests (individual components) - **216 tests**
- Integration tests (end-to-end pipeline) - **6 tests**
- Web frontend/backend tests
- Test data fixtures
- Mocking strategies
- Coverage requirements

**Total Test Count**: 216+ tests (100% pass rate)

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests (180+ tests)
│   ├── phase1/
│   │   ├── test_data_ingestion.py        # 19 tests - Exchange API clients
│   │   ├── test_news_aggregation.py      # 18 tests - News fetching
│   │   ├── test_clustering.py            # 17 tests - HDBSCAN clustering
│   │   ├── test_grok_client.py           # X/Twitter integration
│   │   └── test_multi_timeframe_detection.py  # 15 tests - Multi-timeframe
│   ├── phase2/
│   │   ├── test_journalist_agent.py      # 9 tests - Narrative generation
│   │   ├── test_agent_tools.py           # 27 tests - Tool execution
│   │   └── test_llm_client.py            # 17 tests - LLM wrapper
│   ├── phase3/
│   │   ├── test_validation_engine.py     # 11 tests - Orchestrator
│   │   ├── test_validators.py            # 16 tests - Rule validators
│   │   └── test_registry_and_judge.py    # 16 tests - Registry + LLM judge
│   └── orchestration/
│       ├── test_pipeline.py              # 23 tests - Pipeline orchestration
│       └── test_scheduler.py             # 17 tests - Scheduler
├── integration/
│   └── test_full_pipeline.py   # 6 tests - End-to-end workflows
├── fixtures/
│   ├── sample_prices.json      # Mock price data
│   ├── sample_news.json        # Mock news data
│   └── sample_anomalies.json   # Mock anomalies
└── web/                        # Web tests (separate)
    ├── backend/
    │   └── tests/              # Express API tests
    └── frontend/
        └── src/__tests__/      # React component tests
```

## Running Tests

### Quick Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/phase1/test_statistical.py

# Run specific test
pytest tests/unit/phase1/test_statistical.py::test_zscore_detects_spike

# Run tests matching pattern
pytest -k "zscore"

# Run with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Run only fast tests (skip integration)
pytest -m "not integration"

# Run integration tests
pytest -m integration
```

### Continuous Testing

```bash
# Watch mode (requires pytest-watch)
pip install pytest-watch
ptw
```

## Unit Tests

### Testing Statistical Detectors

```python
# tests/unit/phase1/test_statistical.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.phase1_detector.anomaly_detection.statistical import (
    ZScoreDetector,
    BollingerBandDetector,
    AnomalyDetector
)
from src.phase1_detector.anomaly_detection.models import AnomalyType


class TestZScoreDetector:
    """Test Z-score anomaly detector."""

    @pytest.fixture
    def normal_prices(self):
        """Generate normal price data (no anomaly)."""
        return pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
            'price': [45000 + i * 0.1 for i in range(60)],  # Gradual increase
            'volume': [1000] * 60,
            'symbol': ['BTC-USD'] * 60
        })

    @pytest.fixture
    def spike_prices(self):
        """Generate price data with spike."""
        prices = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
            'price': [45000] * 60,
            'volume': [1000] * 60,
            'symbol': ['BTC-USD'] * 60
        })
        # Add 5% spike at index 55
        prices.loc[55, 'price'] = 47250
        return prices

    def test_no_anomaly_on_normal_data(self, normal_prices):
        """Should not detect anomaly in normal price movements."""
        detector = ZScoreDetector(threshold=3.0, window_minutes=60)
        anomalies = detector.detect(normal_prices)

        assert len(anomalies) == 0

    def test_detects_price_spike(self, spike_prices):
        """Should detect significant price spike."""
        detector = ZScoreDetector(threshold=3.0, window_minutes=60)
        anomalies = detector.detect(spike_prices)

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.PRICE_SPIKE
        assert anomalies[0].z_score > 3.0
        assert anomalies[0].price_change_pct > 4.0

    def test_threshold_tuning(self, spike_prices):
        """Higher threshold should reduce detections."""
        detector_low = ZScoreDetector(threshold=2.0, window_minutes=60)
        detector_high = ZScoreDetector(threshold=5.0, window_minutes=60)

        anomalies_low = detector_low.detect(spike_prices)
        anomalies_high = detector_high.detect(spike_prices)

        assert len(anomalies_low) >= len(anomalies_high)

    def test_insufficient_data(self):
        """Should handle insufficient data gracefully."""
        prices = pd.DataFrame({
            'timestamp': [datetime.now()],
            'price': [45000],
            'volume': [1000],
            'symbol': ['BTC-USD']
        })

        detector = ZScoreDetector(threshold=3.0, window_minutes=60)
        anomalies = detector.detect(prices)

        assert len(anomalies) == 0


class TestBollingerBandDetector:
    """Test Bollinger Band detector."""

    def test_detects_breakout(self):
        """Should detect price breaking upper band."""
        # Generate stable prices within bands
        prices = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(30, 0, -1)],
            'price': [45000 + (i % 5) * 10 for i in range(30)],  # Small oscillation
            'volume': [1000] * 30,
            'symbol': ['BTC-USD'] * 30
        })
        # Add breakout
        prices.loc[28, 'price'] = 46000

        detector = BollingerBandDetector(window=20, std_multiplier=2.0)
        anomalies = detector.detect(prices)

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type in [AnomalyType.PRICE_SPIKE, AnomalyType.PRICE_DROP]


class TestCombinedDetector:
    """Test combined price + volume detector."""

    def test_detects_combined_anomaly(self):
        """Should detect when both price and volume spike."""
        prices = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
            'price': [45000] * 60,
            'volume': [1000] * 60,
            'symbol': ['BTC-USD'] * 60
        })
        # Add combined anomaly
        prices.loc[55, 'price'] = 47000  # Price spike
        prices.loc[55, 'volume'] = 5000  # Volume spike

        detector = AnomalyDetector()
        anomalies = detector.detect_all(prices)

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.COMBINED
        assert anomalies[0].confidence > 0.8
```

### Testing Database Models

```python
# tests/unit/database/test_models.py
import pytest
from datetime import datetime
from src.database.models import Anomaly, Narrative, AnomalyTypeEnum


def test_anomaly_creation():
    """Test creating anomaly instance."""
    anomaly = Anomaly(
        symbol="BTC-USD",
        detected_at=datetime.now(),
        anomaly_type=AnomalyTypeEnum.PRICE_SPIKE,
        z_score=3.5,
        price_change_pct=4.5,
        confidence=0.9
    )

    assert anomaly.symbol == "BTC-USD"
    assert anomaly.anomaly_type == AnomalyTypeEnum.PRICE_SPIKE
    assert anomaly.z_score == 3.5


def test_anomaly_narrative_relationship():
    """Test anomaly-narrative relationship."""
    anomaly = Anomaly(
        symbol="BTC-USD",
        detected_at=datetime.now(),
        anomaly_type=AnomalyTypeEnum.PRICE_DROP,
        z_score=-3.5,
        price_change_pct=-5.2,
        confidence=0.9
    )

    narrative = Narrative(
        anomaly=anomaly,
        narrative_text="Bitcoin dropped 5.2% at 2:15 PM UTC.",
        validation_passed=True,
        llm_provider="anthropic"
    )

    assert narrative.anomaly == anomaly
    assert anomaly.narrative == narrative
```

## Integration Tests

### Testing Full Pipeline

```python
# tests/integration/test_pipeline.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.orchestration.pipeline import AnomalyPipeline
from src.database.connection import get_db_context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_pipeline(test_db):
    """Test complete pipeline: detection → clustering → narrative → validation."""

    # 1. Inject mock price data with anomaly
    prices = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
        'price': [45000] * 60,
        'volume': [1000] * 60,
        'symbol': ['BTC-USD'] * 60
    })
    prices.loc[55, 'price'] = 47000  # 4.4% spike

    # 2. Mock news data (simulating API response)
    mock_news = [
        {
            'title': 'Bitcoin surges on positive ETF news',
            'published_at': datetime.now() - timedelta(minutes=10),
            'source': 'cryptopanic'
        },
        {
            'title': 'BTC rallies after Fed announcement',
            'published_at': datetime.now() - timedelta(minutes=12),
            'source': 'newsapi'
        }
    ]

    # 3. Initialize pipeline with mocks
    pipeline = AnomalyPipeline(
        detector=...,
        news_aggregator=MockNewsAggregator(mock_news),
        clusterer=...,
        journalist=...,
        skeptic=...,
        db=test_db
    )

    # 4. Run pipeline
    result = await pipeline.run('BTC-USD')

    # 5. Verify results
    assert result is not None
    assert "4.4%" in result or "4%" in result
    assert "surge" in result.lower() or "rally" in result.lower()

    # 6. Verify database persistence
    with get_db_context() as db:
        anomalies = db.query(Anomaly).filter(Anomaly.symbol == 'BTC-USD').all()
        assert len(anomalies) == 1

        narrative = db.query(Narrative).filter(
            Narrative.anomaly_id == anomalies[0].id
        ).first()
        assert narrative is not None
        assert narrative.validation_passed is True
```

### Testing Database Operations

```python
# tests/integration/test_database.py
import pytest
from datetime import datetime
from src.database.models import Base, Anomaly, Narrative
from src.database.connection import init_database, get_db_session
from sqlalchemy import create_engine


@pytest.fixture(scope="module")
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create test database session."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def test_save_anomaly(db_session):
    """Test saving anomaly to database."""
    anomaly = Anomaly(
        symbol="BTC-USD",
        detected_at=datetime.now(),
        anomaly_type="price_spike",
        z_score=3.5,
        price_change_pct=4.5,
        confidence=0.9
    )

    db_session.add(anomaly)
    db_session.commit()

    # Query back
    retrieved = db_session.query(Anomaly).filter(
        Anomaly.symbol == "BTC-USD"
    ).first()

    assert retrieved is not None
    assert retrieved.z_score == 3.5


def test_cascade_delete(db_session):
    """Test that deleting anomaly deletes narrative."""
    anomaly = Anomaly(
        symbol="BTC-USD",
        detected_at=datetime.now(),
        anomaly_type="price_spike",
        z_score=3.5,
        price_change_pct=4.5,
        confidence=0.9
    )

    narrative = Narrative(
        anomaly=anomaly,
        narrative_text="Test narrative",
        validation_passed=True
    )

    db_session.add(anomaly)
    db_session.add(narrative)
    db_session.commit()

    anomaly_id = anomaly.id

    # Delete anomaly
    db_session.delete(anomaly)
    db_session.commit()

    # Verify narrative was deleted
    narratives = db_session.query(Narrative).filter(
        Narrative.anomaly_id == anomaly_id
    ).all()

    assert len(narratives) == 0
```

## Test Fixtures

### Shared Fixtures

```python
# tests/conftest.py
import pytest
import pandas as pd
from datetime import datetime, timedelta
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
    """Standard BTC price data for testing."""
    return pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)],
        'price': [45000 + i * 10 for i in range(60)],
        'volume': [1000] * 60,
        'symbol': ['BTC-USD'] * 60
    })


@pytest.fixture
def sample_news_articles():
    """Standard news articles for testing."""
    return [
        {
            'title': 'Bitcoin surges on ETF approval',
            'published_at': datetime.now() - timedelta(minutes=10),
            'source': 'cryptopanic',
            'url': 'https://example.com/article1'
        },
        {
            'title': 'BTC rallies after Fed announcement',
            'published_at': datetime.now() - timedelta(minutes=15),
            'source': 'newsapi',
            'url': 'https://example.com/article2'
        }
    ]
```

### Fixture Files

```json
// tests/fixtures/sample_prices.json
{
  "symbol": "BTC-USD",
  "prices": [
    {"timestamp": "2024-01-15T14:00:00Z", "price": 45000, "volume": 1000},
    {"timestamp": "2024-01-15T14:01:00Z", "price": 45100, "volume": 1100},
    {"timestamp": "2024-01-15T14:15:00Z", "price": 47000, "volume": 5000}
  ]
}
```

## Mocking Strategies

### Mocking External APIs

```python
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_coinbase_client():
    """Mock Coinbase API client."""
    client = Mock()
    client.get_price.return_value = {
        'price': 45000,
        'volume': 1000,
        'timestamp': datetime.now()
    }
    return client


def test_with_mocked_api(mock_coinbase_client):
    """Test using mocked API."""
    price = mock_coinbase_client.get_price('BTC-USD')
    assert price['price'] == 45000


@patch('src.phase1_detector.data_ingestion.coinbase_client.CoinbaseClient')
def test_with_patch(MockCoinbaseClient):
    """Test using patch decorator."""
    mock_instance = MockCoinbaseClient.return_value
    mock_instance.get_price.return_value = {'price': 45000}

    # Test code that uses CoinbaseClient
    # ...
```

### Mocking LLM Calls

```python
@pytest.fixture
def mock_llm_client():
    """Mock LiteLLM client."""
    client = Mock()
    client.complete.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content="Bitcoin dropped 5.2% at 2:15 PM UTC. The move followed SEC news."
                ),
                finish_reason="stop"
            )
        ]
    )
    return client
```

## Coverage Requirements

### Target Coverage

- **Overall**: 80% minimum
- **Critical paths**: 95%+ (detectors, validation)
- **Database models**: 100%
- **Utils**: 90%

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Fail if below threshold
pytest --cov=src --cov-fail-under=80
```

### Coverage Configuration

```ini
# .coveragerc
[run]
source = src
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

## Test Markers

Define custom markers in `pytest.ini`:

```ini
[pytest]
markers =
    integration: marks tests as integration tests (slow)
    unit: marks tests as unit tests (fast)
    slow: marks tests as slow
    api: marks tests that call external APIs
```

**Usage**:
```python
@pytest.mark.integration
def test_full_pipeline():
    pass

@pytest.mark.slow
@pytest.mark.api
def test_real_coinbase_api():
    pass
```

**Run specific markers**:
```bash
pytest -m unit          # Only unit tests
pytest -m "not slow"    # Skip slow tests
pytest -m "integration and not api"
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: testpassword
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

## Web Testing

### Backend API Tests

**Location**: `web/backend/tests/`

**Test Framework**: Jest + Supertest

```bash
cd web/backend
npm test                # Run all tests
npm run test:watch      # Watch mode
npm run test:coverage   # Coverage report
```

**Example Test**:
```typescript
// tests/routes/auth.test.ts
import request from 'supertest';
import { app } from '../../src/index';

describe('POST /auth/login', () => {
  it('should return JWT token on valid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({
        email: 'test@example.com',
        password: 'password123'
      });

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('user');
    expect(res.headers['set-cookie']).toBeDefined();
  });

  it('should return 401 on invalid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({
        email: 'test@example.com',
        password: 'wrong'
      });

    expect(res.status).toBe(401);
    expect(res.body).toHaveProperty('error');
  });
});
```

**Coverage Areas**:
- Authentication endpoints (register, login, logout)
- Anomaly CRUD operations
- News filtering and pagination
- Price history queries
- JWT middleware
- Rate limiting
- Error handling

---

### Frontend Component Tests

**Location**: `web/frontend/src/__tests__/`

**Test Framework**: Vitest + React Testing Library

```bash
cd web/frontend
npm test                # Run all tests
npm run test:watch      # Watch mode
npm run test:ui         # Vitest UI
npm run test:coverage   # Coverage report
```

**Example Test**:
```typescript
// src/__tests__/components/AnomalyCard.test.tsx
import { render, screen } from '@testing-library/react';
import { AnomalyCard } from '../../components/dashboard/AnomalyCard';

describe('AnomalyCard', () => {
  it('renders anomaly information', () => {
    const anomaly = {
      id: '123',
      symbol: 'BTC-USD',
      anomaly_type: 'price_drop',
      price_change_pct: -5.2,
      confidence: 0.89,
      detected_at: '2024-01-15T14:15:00Z'
    };

    render(<AnomalyCard anomaly={anomaly} />);

    expect(screen.getByText('BTC-USD')).toBeInTheDocument();
    expect(screen.getByText('-5.2%')).toBeInTheDocument();
    expect(screen.getByText('price_drop')).toBeInTheDocument();
  });

  it('applies correct styling for price drop', () => {
    const anomaly = { /* ... */ anomaly_type: 'price_drop' };
    render(<AnomalyCard anomaly={anomaly} />);

    const card = screen.getByTestId('anomaly-card');
    expect(card).toHaveClass('border-red-500');
  });
});
```

**Coverage Areas**:
- Dashboard components (LiveIndicator, AnomalyCard, SymbolSelector)
- Chart components (PriceChart, TimeRangeSelector)
- Browser components (Filters, Pagination)
- Hooks (useAnomalies, usePrices, useAuth)
- API client functions
- Error boundaries

---

### End-to-End Tests (Future)

**Recommended**: Playwright or Cypress for full E2E testing

```bash
# Example Playwright test
cd web/frontend
npm run test:e2e
```

**Test Scenarios**:
1. User registration and login flow
2. View dashboard with live anomalies
3. Click anomaly card → view detail page
4. Filter anomalies by symbol and date
5. View price chart with anomaly markers
6. Export anomaly data to JSON
7. Logout

---

## Test Coverage Summary

### Python Backend

| Module | Tests | Coverage |
|--------|-------|----------|
| Phase 1: Data Ingestion | 19 | 84% |
| Phase 1: News Aggregation | 18 | 85% |
| Phase 1: Clustering | 17 | 90% |
| Phase 1: Multi-timeframe | 15 | 95% |
| Phase 2: LLM Client | 17 | 88% |
| Phase 2: Agent Tools | 27 | 92% |
| Phase 2: Journalist | 9 | 85% |
| Phase 3: Validators | 16 | 90% |
| Phase 3: Engine | 11 | 88% |
| Phase 3: Registry | 16 | 90% |
| Orchestration: Pipeline | 23 | 92% |
| Orchestration: Scheduler | 17 | 90% |
| Integration Tests | 6 | - |
| **Total** | **216** | **89%** |

### Web Backend (TypeScript)

| Module | Status |
|--------|--------|
| Authentication | ⏳ Planned |
| Anomaly Routes | ⏳ Planned |
| News Routes | ⏳ Planned |
| Price Routes | ⏳ Planned |
| Middleware | ⏳ Planned |

### Web Frontend (TypeScript)

| Module | Status |
|--------|--------|
| Dashboard Components | ⏳ Planned |
| Chart Components | ⏳ Planned |
| Hooks | ⏳ Planned |
| API Client | ⏳ Planned |

---

## Best Practices

1. **Test naming**: Use descriptive names (`test_detects_price_spike` not `test1`)
2. **One assertion per test**: Keep tests focused
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Use fixtures**: Avoid code duplication
5. **Mock external services**: Tests should be fast and reliable
6. **Test edge cases**: Null values, empty data, extreme values
7. **Test error handling**: Verify exceptions are raised correctly
8. **Maintain test data**: Keep fixtures updated with schema changes
9. **Run tests before commits**: Use pre-commit hooks
10. **Monitor coverage**: Aim for 80%+ overall, 95%+ for critical paths

---

**Happy testing!** Well-tested code is maintainable code.
