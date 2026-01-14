"""Integration tests for complete Phase 1→2→3 pipeline flow.

These tests verify the end-to-end integration of all three phases.
They use mocked external APIs (LLM, crypto exchanges, news APIs) to avoid
real API calls, but test the actual database integration and data flow.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import pandas as pd

from src.orchestration.pipeline import MarketAnomalyPipeline
from src.database.models import Anomaly, NewsArticle, Narrative
from src.phase1_detector.anomaly_detection.models import DetectedAnomaly, AnomalyType
from src.phase1_detector.news_aggregation.models import NewsArticle as NewsArticlePydantic


@pytest.fixture
def integration_settings():
    """Settings for integration tests."""
    settings = Mock()
    settings.database.url = "postgresql://user:pass@localhost/test_mane"
    settings.data_ingestion.primary_source = "coinbase"
    settings.data_ingestion.coinbase_api_key = None
    settings.data_ingestion.coinbase_api_secret = None
    settings.data_ingestion.poll_interval_seconds = 60
    settings.orchestration.duplicate_window_minutes = 5
    settings.orchestration.price_history_lookback_minutes = 60
    settings.orchestration.min_price_points = 30
    settings.detection.news_window_minutes = 30
    settings.detection.symbols = ["BTC-USD"]
    settings.llm.provider = "anthropic"
    settings.llm.model = "claude-3-5-haiku-20241022"
    settings.llm.temperature = 0.3
    settings.llm.max_tokens = 500
    settings.llm.anthropic_api_key = "test-key"
    settings.validation.pass_threshold = 0.65
    return settings


@pytest.fixture
def mock_price_history():
    """Mock price history DataFrame with anomaly."""
    timestamps = pd.date_range(end=datetime.utcnow(), periods=60, freq="1min")
    # Create price spike anomaly
    prices = [45000.0] * 55 + [50000.0, 51000.0, 52000.0, 53000.0, 54000.0]
    volumes = [1000000.0] * 60
    symbols = ["BTC-USD"] * 60

    return pd.DataFrame({
        "timestamp": timestamps,
        "price": prices,
        "volume": volumes,
        "symbol": symbols,
    })


@pytest.fixture
def mock_news_articles():
    """Mock news articles related to the anomaly."""
    now = datetime.utcnow()
    return [
        NewsArticlePydantic(
            source="cryptopanic",
            title="Bitcoin Surges on Major Institutional Investment",
            url="https://example.com/news/1",
            published_at=now - timedelta(minutes=10),
            summary="Major investment fund announces $1B Bitcoin purchase",
            sentiment=0.8,
            symbols=["BTC-USD"],
            timing_tag="pre_event",
            time_diff_minutes=-10.0,
        ),
        NewsArticlePydantic(
            source="reddit",
            title="BTC breaking resistance levels",
            url="https://reddit.com/r/crypto/abc",
            published_at=now - timedelta(minutes=5),
            summary="Technical analysis shows BTC breaking key resistance",
            sentiment=0.6,
            symbols=["BTC-USD"],
            timing_tag="pre_event",
            time_diff_minutes=-5.0,
        ),
    ]


@pytest.fixture
def mock_llm_narrative():
    """Mock LLM-generated narrative."""
    return Mock(
        narrative_text="Bitcoin surged 11% following a $1B institutional investment announcement. Technical resistance levels were also broken.",
        confidence_score=0.85,
        tools_used=["verify_timestamp", "sentiment_check"],
        tool_results={"verify_timestamp": {"causal": True}, "sentiment_check": {"avg_sentiment": 0.7}},
        id="test-narrative-id",
    )


@pytest.fixture
def mock_validation_result():
    """Mock validation result."""
    return Mock(
        validated=True,
        validation_passed=True,
        validation_reason="Narrative is causally sound with strong sentiment alignment",
        aggregate_score=0.82,
        confidence=0.9,
    )


class TestFullPipelineIntegration:
    """Test complete pipeline flow from detection to validation."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_pipeline_with_anomaly(
        self,
        integration_settings,
        mock_price_history,
        mock_news_articles,
        mock_llm_narrative,
        mock_validation_result,
    ):
        """Test complete pipeline execution when anomaly is detected.

        Flow:
        1. Fetch price history → Detect anomaly
        2. Fetch and cluster news
        3. Generate narrative
        4. Validate narrative
        """
        # Create pipeline with mocked components
        with patch("src.orchestration.pipeline.CoinbaseClient") as MockClient, \
             patch("src.orchestration.pipeline.init_database"):

            # Mock crypto client
            mock_crypto_client = MockClient.return_value
            mock_crypto_client.get_price_history = AsyncMock(
                return_value=mock_price_history
            )

            # Mock news aggregator
            with patch("src.orchestration.pipeline.NewsAggregator") as MockAggregator:
                mock_aggregator = MockAggregator.return_value
                mock_aggregator.get_news_for_anomaly = AsyncMock(
                    return_value=mock_news_articles
                )

                # Mock journalist agent
                with patch("src.orchestration.pipeline.JournalistAgent") as MockJournalist:
                    mock_journalist = MockJournalist.return_value
                    mock_journalist.generate_narrative = AsyncMock(
                        return_value=mock_llm_narrative
                    )

                    # Mock validation engine
                    with patch("src.orchestration.pipeline.ValidationEngine") as MockValidator:
                        mock_validator = MockValidator.return_value
                        mock_validator.validate_narrative = AsyncMock(
                            return_value=mock_validation_result
                        )

                        # Create mock session
                        mock_session = Mock()
                        mock_session.query().filter().order_by().first.return_value = None  # No duplicate
                        mock_session.query().filter().options().first.return_value = Mock()
                        mock_session.add = Mock()
                        mock_session.commit = Mock()
                        mock_session.refresh = Mock()

                        # Create pipeline
                        pipeline = MarketAnomalyPipeline(integration_settings)

                        # Run pipeline
                        anomaly, stats = await pipeline.run_for_symbol("BTC-USD", mock_session)

                        # Verify success
                        assert stats.success is True
                        assert stats.phase_reached == "complete"
                        assert stats.anomaly_detected is True
                        assert stats.news_count == 2
                        assert stats.narrative_validated is True
                        assert stats.execution_time_seconds > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_without_anomaly(
        self,
        integration_settings,
    ):
        """Test pipeline when no anomaly is detected."""
        # Create normal (non-anomalous) price history
        normal_prices = pd.DataFrame({
            "timestamp": pd.date_range(end=datetime.utcnow(), periods=60, freq="1min"),
            "price": [45000.0] * 60,  # Flat prices, no anomaly
            "volume": [1000000.0] * 60,
            "symbol": ["BTC-USD"] * 60,
        })

        with patch("src.orchestration.pipeline.CoinbaseClient") as MockClient:
            mock_crypto_client = MockClient.return_value
            mock_crypto_client.get_price_history = AsyncMock(
                return_value=normal_prices
            )

            mock_session = Mock()
            mock_session.query().filter().order_by().first.return_value = None

            pipeline = MarketAnomalyPipeline(integration_settings)
            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", mock_session)

            # Verify no anomaly detected
            assert anomaly is None
            assert stats.success is True
            assert stats.phase_reached == "detection_complete"
            assert stats.anomaly_detected is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_news_failure(
        self,
        integration_settings,
        mock_price_history,
        mock_llm_narrative,
        mock_validation_result,
    ):
        """Test pipeline continues when news fetch fails."""
        with patch("src.orchestration.pipeline.CoinbaseClient") as MockClient, \
             patch("src.orchestration.pipeline.NewsAggregator") as MockAggregator, \
             patch("src.orchestration.pipeline.JournalistAgent") as MockJournalist, \
             patch("src.orchestration.pipeline.ValidationEngine") as MockValidator:

            # Mock crypto client
            MockClient.return_value.get_price_history = AsyncMock(
                return_value=mock_price_history
            )

            # Mock news aggregator to fail
            MockAggregator.return_value.get_news_for_anomaly = AsyncMock(
                side_effect=Exception("News API timeout")
            )

            # Mock journalist and validator
            MockJournalist.return_value.generate_narrative = AsyncMock(
                return_value=mock_llm_narrative
            )
            MockValidator.return_value.validate_narrative = AsyncMock(
                return_value=mock_validation_result
            )

            mock_session = Mock()
            mock_session.query().filter().order_by().first.return_value = None
            mock_session.query().filter().options().first.return_value = Mock()
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()

            pipeline = MarketAnomalyPipeline(integration_settings)
            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", mock_session)

            # Verify pipeline completed despite news failure
            assert stats.success is True
            assert stats.phase_reached == "complete"
            assert stats.news_count == 0  # No news fetched
            assert stats.narrative_validated is True  # Still validated

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_duplicate_anomaly(
        self,
        integration_settings,
        mock_price_history,
    ):
        """Test pipeline skips processing when duplicate anomaly exists."""
        with patch("src.orchestration.pipeline.CoinbaseClient"):
            # Create existing anomaly
            existing_anomaly = Mock(spec=Anomaly)
            existing_anomaly.id = "existing-id"
            existing_anomaly.detected_at = datetime.utcnow() - timedelta(minutes=2)

            mock_session = Mock()
            mock_session.query().filter().order_by().first.return_value = existing_anomaly

            pipeline = MarketAnomalyPipeline(integration_settings)
            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", mock_session)

            # Verify early exit
            assert anomaly == existing_anomaly
            assert stats.success is True
            assert stats.phase_reached == "duplicate_found"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_validation_failure(
        self,
        integration_settings,
        mock_price_history,
        mock_news_articles,
        mock_llm_narrative,
    ):
        """Test pipeline when narrative validation fails."""
        # Mock validation failure
        failed_validation = Mock(
            validated=True,
            validation_passed=False,
            validation_reason="Sentiment mismatch with price movement",
            aggregate_score=0.45,
            confidence=0.7,
        )

        with patch("src.orchestration.pipeline.CoinbaseClient") as MockClient, \
             patch("src.orchestration.pipeline.NewsAggregator") as MockAggregator, \
             patch("src.orchestration.pipeline.JournalistAgent") as MockJournalist, \
             patch("src.orchestration.pipeline.ValidationEngine") as MockValidator:

            MockClient.return_value.get_price_history = AsyncMock(
                return_value=mock_price_history
            )
            MockAggregator.return_value.get_news_for_anomaly = AsyncMock(
                return_value=mock_news_articles
            )
            MockJournalist.return_value.generate_narrative = AsyncMock(
                return_value=mock_llm_narrative
            )
            MockValidator.return_value.validate_narrative = AsyncMock(
                return_value=failed_validation
            )

            mock_session = Mock()
            mock_session.query().filter().order_by().first.return_value = None
            mock_session.query().filter().options().first.return_value = Mock()
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()

            pipeline = MarketAnomalyPipeline(integration_settings)
            anomaly, stats = await pipeline.run_for_symbol("BTC-USD", mock_session)

            # Verify pipeline completed but validation failed
            assert stats.success is True
            assert stats.phase_reached == "complete"
            assert stats.narrative_validated is False  # Validation failed


class TestDataFlowIntegration:
    """Test data flow and model conversions between phases."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pydantic_to_orm_conversion(self, integration_settings, mock_price_history):
        """Test conversion from Pydantic DetectedAnomaly to ORM Anomaly."""
        with patch("src.orchestration.pipeline.CoinbaseClient"):
            mock_session = Mock()
            mock_session.query().filter().order_by().first.return_value = None
            mock_session.add = Mock()
            mock_session.commit = Mock()

            # Capture the ORM model passed to session.add
            added_models = []
            mock_session.add = lambda model: added_models.append(model)

            pipeline = MarketAnomalyPipeline(integration_settings)

            # Create detected anomaly (Pydantic)
            detected = DetectedAnomaly(
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

            # Convert to ORM
            orm_anomaly = pipeline._persist_anomaly(detected, mock_session)

            # Verify conversion
            assert isinstance(orm_anomaly, Anomaly)
            assert orm_anomaly.symbol == "BTC-USD"
            assert orm_anomaly.z_score == 4.5
            assert orm_anomaly.confidence == 0.95
