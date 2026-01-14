"""Unit tests for pipeline orchestrator."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import pandas as pd

from src.orchestration.pipeline import MarketAnomalyPipeline, PipelineStats
from src.phase1_detector.anomaly_detection.models import DetectedAnomaly, AnomalyType
from src.database.models import Anomaly, AnomalyTypeEnum


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.data_ingestion.primary_source = "coinbase"
    settings.data_ingestion.coinbase_api_key = None
    settings.data_ingestion.coinbase_api_secret = None
    settings.orchestration.duplicate_window_minutes = 5
    settings.orchestration.price_history_lookback_minutes = 60
    settings.orchestration.min_price_points = 30
    settings.detection.news_window_minutes = 30
    return settings


@pytest.fixture
def pipeline(mock_settings):
    """Create pipeline instance with mocked components."""
    with patch("src.orchestration.pipeline.CoinbaseClient"), \
         patch("src.orchestration.pipeline.AnomalyDetector"), \
         patch("src.orchestration.pipeline.NewsAggregator"), \
         patch("src.orchestration.pipeline.NewsClusterer"), \
         patch("src.orchestration.pipeline.LLMClient"), \
         patch("src.orchestration.pipeline.JournalistAgent"), \
         patch("src.orchestration.pipeline.ValidationEngine"):

        pipeline = MarketAnomalyPipeline(mock_settings)
        return pipeline


@pytest.fixture
def sample_price_df():
    """Sample price DataFrame with anomaly."""
    timestamps = pd.date_range(end=datetime.utcnow(), periods=60, freq="1min")
    prices = [45000.0] * 55 + [50000.0] * 5  # Price spike at end
    volumes = [1000000.0] * 60
    symbols = ["BTC-USD"] * 60

    return pd.DataFrame({
        "timestamp": timestamps,
        "price": prices,
        "volume": volumes,
        "symbol": symbols,
    })


@pytest.fixture
def sample_detected_anomaly():
    """Sample detected anomaly (Pydantic model)."""
    return DetectedAnomaly(
        symbol="BTC-USD",
        detected_at=datetime.utcnow(),
        anomaly_type=AnomalyType.PRICE_SPIKE,
        z_score=4.5,
        price_change_pct=11.1,
        volume_change_pct=0.0,
        confidence=0.95,
        baseline_window_minutes=60,
        price_before=45000.0,
        price_at_detection=50000.0,
        volume_before=1000000.0,
        volume_at_detection=1000000.0,
    )


class TestCheckDuplicateAnomaly:
    """Tests for _check_duplicate_anomaly method."""

    def test_no_duplicate(self, pipeline):
        """Test when no duplicate exists."""
        session = Mock()
        session.query().filter().order_by().first.return_value = None

        result = pipeline._check_duplicate_anomaly(
            "BTC-USD",
            datetime.utcnow(),
            session,
        )

        assert result is None

    def test_duplicate_found(self, pipeline):
        """Test when duplicate exists within window."""
        session = Mock()
        duplicate = Mock(spec=Anomaly)
        duplicate.id = "test-id"
        duplicate.detected_at = datetime.utcnow() - timedelta(minutes=2)
        session.query().filter().order_by().first.return_value = duplicate

        result = pipeline._check_duplicate_anomaly(
            "BTC-USD",
            datetime.utcnow(),
            session,
        )

        assert result == duplicate


class TestFetchPriceHistory:
    """Tests for _fetch_price_history method."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self, pipeline, sample_price_df):
        """Test successful price history fetch."""
        session = Mock()
        pipeline.crypto_client.get_price_history = AsyncMock(
            return_value=sample_price_df
        )

        result = await pipeline._fetch_price_history("BTC-USD", session)

        assert result is not None
        assert len(result) == 60
        assert "timestamp" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_failure(self, pipeline):
        """Test price history fetch failure."""
        session = Mock()
        pipeline.crypto_client.get_price_history = AsyncMock(
            side_effect=Exception("API error")
        )

        result = await pipeline._fetch_price_history("BTC-USD", session)

        assert result is None


class TestDetectAnomaly:
    """Tests for _detect_anomaly method."""

    @pytest.mark.asyncio
    async def test_anomaly_detected(self, pipeline, sample_price_df, sample_detected_anomaly):
        """Test successful anomaly detection."""
        pipeline.detector.detect_all = Mock(return_value=[sample_detected_anomaly])

        result = await pipeline._detect_anomaly(sample_price_df)

        assert result is not None
        assert result.symbol == "BTC-USD"
        assert result.anomaly_type == AnomalyType.PRICE_SPIKE
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_no_anomaly_detected(self, pipeline, sample_price_df):
        """Test when no anomaly is detected."""
        pipeline.detector.detect_all = Mock(return_value=[])

        result = await pipeline._detect_anomaly(sample_price_df)

        assert result is None


class TestPersistAnomaly:
    """Tests for _persist_anomaly method."""

    def test_pydantic_to_orm_conversion(self, pipeline, sample_detected_anomaly):
        """Test conversion from Pydantic to ORM model."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()

        result = pipeline._persist_anomaly(sample_detected_anomaly, session)

        # Verify ORM model created
        assert isinstance(result, Anomaly)
        assert result.symbol == "BTC-USD"
        assert result.anomaly_type == AnomalyTypeEnum.PRICE_SPIKE
        assert result.z_score == 4.5
        assert result.confidence == 0.95

        # Verify database operations called
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    def test_enum_conversion(self, pipeline, sample_detected_anomaly):
        """Test correct enum conversion."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.refresh = Mock()

        # Test all anomaly types
        test_cases = [
            (AnomalyType.PRICE_SPIKE, AnomalyTypeEnum.PRICE_SPIKE),
            (AnomalyType.PRICE_DROP, AnomalyTypeEnum.PRICE_DROP),
            (AnomalyType.VOLUME_SPIKE, AnomalyTypeEnum.VOLUME_SPIKE),
            (AnomalyType.COMBINED, AnomalyTypeEnum.COMBINED),
        ]

        for pydantic_type, expected_orm_type in test_cases:
            sample_detected_anomaly.anomaly_type = pydantic_type
            result = pipeline._persist_anomaly(sample_detected_anomaly, session)
            assert result.anomaly_type == expected_orm_type


class TestRunForSymbol:
    """Tests for run_for_symbol method (main pipeline flow)."""

    @pytest.mark.asyncio
    async def test_duplicate_found_early_exit(self, pipeline):
        """Test early exit when duplicate anomaly found."""
        session = Mock()
        duplicate = Mock(spec=Anomaly)
        duplicate.id = "existing-id"

        with patch.object(pipeline, "_check_duplicate_anomaly", return_value=duplicate):
            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", session)

        assert anomaly == duplicate
        assert stats.success is True
        assert stats.phase_reached == "duplicate_found"

    @pytest.mark.asyncio
    async def test_insufficient_price_history(self, pipeline):
        """Test handling of insufficient price history."""
        session = Mock()
        short_df = pd.DataFrame({
            "timestamp": pd.date_range(end=datetime.utcnow(), periods=10, freq="1min"),
            "price": [45000.0] * 10,
            "volume": [1000000.0] * 10,
            "symbol": ["BTC-USD"] * 10,
        })

        with patch.object(pipeline, "_check_duplicate_anomaly", return_value=None), \
             patch.object(pipeline, "_fetch_price_history", return_value=short_df):

            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", session)

        assert anomaly is None
        assert stats.success is False
        assert "Insufficient price history" in stats.error_message

    @pytest.mark.asyncio
    async def test_no_anomaly_detected(self, pipeline, sample_price_df):
        """Test handling when no anomaly is detected."""
        session = Mock()

        with patch.object(pipeline, "_check_duplicate_anomaly", return_value=None), \
             patch.object(pipeline, "_fetch_price_history", return_value=sample_price_df), \
             patch.object(pipeline, "_detect_anomaly", return_value=None):

            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", session)

        assert anomaly is None
        assert stats.success is True
        assert stats.phase_reached == "detection_complete"
        assert stats.anomaly_detected is False

    @pytest.mark.asyncio
    async def test_news_fetch_failure_continues(self, pipeline, sample_price_df, sample_detected_anomaly):
        """Test pipeline continues when news fetch fails."""
        session = Mock()
        session.query().filter().options().first.return_value = Mock()

        mock_anomaly = Mock(spec=Anomaly)
        mock_anomaly.id = "test-id"

        with patch.object(pipeline, "_check_duplicate_anomaly", return_value=None), \
             patch.object(pipeline, "_fetch_price_history", return_value=sample_price_df), \
             patch.object(pipeline, "_detect_anomaly", return_value=sample_detected_anomaly), \
             patch.object(pipeline, "_persist_anomaly", return_value=mock_anomaly), \
             patch.object(pipeline, "_fetch_and_persist_news", side_effect=Exception("News API error")), \
             patch.object(pipeline, "_cluster_news", return_value=None), \
             patch.object(pipeline, "_generate_narrative", return_value=Mock(id="narrative-id")), \
             patch.object(pipeline, "_validate_narrative", return_value=Mock(validation_passed=True, aggregate_score=0.8)):

            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", session)

        # Pipeline should complete despite news fetch failure
        assert stats.success is True
        assert stats.phase_reached == "complete"
        assert stats.news_count == 0  # No news fetched


class TestPipelineStats:
    """Tests for PipelineStats dataclass."""

    def test_stats_creation(self):
        """Test creating pipeline stats."""
        stats = PipelineStats(
            symbol="BTC-USD",
            success=True,
            phase_reached="complete",
            execution_time_seconds=5.2,
            anomaly_detected=True,
            news_count=15,
            cluster_count=3,
            narrative_validated=True,
            error_message=None,
        )

        assert stats.symbol == "BTC-USD"
        assert stats.success is True
        assert stats.anomaly_detected is True
        assert stats.narrative_validated is True
