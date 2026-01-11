# Testing Guide

## Overview

Comprehensive testing guide for Market Anomaly Narrative Engine covering:
- Unit tests (individual components)
- Integration tests (end-to-end pipeline)
- Test data fixtures
- Mocking strategies
- Coverage requirements

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── phase1/
│   │   ├── test_statistical.py       # Statistical detectors
│   │   ├── test_clustering.py        # News clustering
│   │   └── test_data_ingestion.py    # API clients
│   ├── phase2/
│   │   ├── test_agent.py             # Journalist agent
│   │   └── test_tools.py             # Agent tools
│   └── phase3/
│       └── test_validator.py         # Validation rules
├── integration/
│   ├── test_pipeline.py        # Full pipeline
│   └── test_database.py        # Database operations
└── fixtures/
    ├── sample_prices.json      # Mock price data
    ├── sample_news.json        # Mock news data
    └── sample_anomalies.json   # Mock anomalies
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

## Best Practices

1. **Test naming**: Use descriptive names (`test_detects_price_spike` not `test1`)
2. **One assertion per test**: Keep tests focused
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Use fixtures**: Avoid code duplication
5. **Mock external services**: Tests should be fast and reliable
6. **Test edge cases**: Null values, empty data, extreme values
7. **Test error handling**: Verify exceptions are raised correctly

---

**Happy testing!** Well-tested code is maintainable code.
