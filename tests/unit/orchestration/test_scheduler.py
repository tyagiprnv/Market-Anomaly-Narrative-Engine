"""Unit tests for scheduler."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.orchestration.scheduler import (
    AnomalyDetectionScheduler,
    SchedulerMetrics,
    SymbolMetrics,
)
from src.orchestration.pipeline import PipelineStats


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.database.url = "postgresql://user:pass@localhost/test"
    settings.data_ingestion.poll_interval_seconds = 60
    settings.detection.symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    settings.data_ingestion.primary_source = "coinbase"
    settings.data_ingestion.coinbase_api_key = None
    settings.data_ingestion.coinbase_api_secret = None
    return settings


@pytest.fixture
def scheduler(mock_settings):
    """Create scheduler instance with mocked components."""
    with patch("src.orchestration.scheduler.MarketAnomalyPipeline"):
        scheduler = AnomalyDetectionScheduler(mock_settings)
        return scheduler


@pytest.fixture
def sample_success_stats():
    """Sample successful pipeline stats."""
    return PipelineStats(
        symbol="BTC-USD",
        success=True,
        phase_reached="complete",
        execution_time_seconds=3.5,
        anomaly_detected=True,
        news_count=10,
        cluster_count=2,
        narrative_validated=True,
        error_message=None,
    )


@pytest.fixture
def sample_failure_stats():
    """Sample failed pipeline stats."""
    return PipelineStats(
        symbol="ETH-USD",
        success=False,
        phase_reached="detection",
        execution_time_seconds=1.2,
        anomaly_detected=False,
        news_count=0,
        cluster_count=0,
        narrative_validated=None,
        error_message="API timeout",
    )


class TestSchedulerInitialization:
    """Tests for scheduler initialization."""

    def test_initialization(self, mock_settings):
        """Test scheduler initializes correctly."""
        with patch("src.orchestration.scheduler.MarketAnomalyPipeline"):
            scheduler = AnomalyDetectionScheduler(mock_settings)

            assert scheduler.settings == mock_settings
            assert scheduler.symbols == ["BTC-USD", "ETH-USD", "SOL-USD"]
            assert scheduler.poll_interval == 60
            assert len(scheduler.metrics.symbol_stats) == 3

    def test_symbol_metrics_initialized(self, scheduler):
        """Test symbol metrics are initialized for all symbols."""
        for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
            assert symbol in scheduler.metrics.symbol_stats
            assert isinstance(scheduler.metrics.symbol_stats[symbol], SymbolMetrics)
            assert scheduler.metrics.symbol_stats[symbol].total_runs == 0


class TestStartStop:
    """Tests for start/stop lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start(self, scheduler):
        """Test scheduler starts correctly."""
        with patch("src.orchestration.scheduler.init_database") as mock_init_db:
            scheduler.scheduler.add_job = Mock()
            scheduler.scheduler.start = Mock()

            await scheduler.start()

            # Verify database initialized
            mock_init_db.assert_called_once()

            # Verify jobs added
            assert scheduler.scheduler.add_job.call_count == 2  # price storage + detection

            # Verify scheduler started
            scheduler.scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, scheduler):
        """Test scheduler stops gracefully."""
        scheduler.scheduler.shutdown = Mock()

        await scheduler.stop()

        scheduler.scheduler.shutdown.assert_called_once_with(wait=True)


class TestUpdateMetrics:
    """Tests for _update_metrics method."""

    def test_update_success_metrics(self, scheduler, sample_success_stats):
        """Test metrics update for successful run."""
        initial_total = scheduler.metrics.total_runs
        initial_success = scheduler.metrics.successful_runs
        initial_anomalies = scheduler.metrics.anomalies_detected
        initial_validated = scheduler.metrics.narratives_validated

        scheduler._update_metrics(sample_success_stats)

        assert scheduler.metrics.total_runs == initial_total + 1
        assert scheduler.metrics.successful_runs == initial_success + 1
        assert scheduler.metrics.anomalies_detected == initial_anomalies + 1
        assert scheduler.metrics.narratives_validated == initial_validated + 1

    def test_update_failure_metrics(self, scheduler, sample_failure_stats):
        """Test metrics update for failed run."""
        initial_total = scheduler.metrics.total_runs
        initial_failed = scheduler.metrics.failed_runs

        scheduler._update_metrics(sample_failure_stats)

        assert scheduler.metrics.total_runs == initial_total + 1
        assert scheduler.metrics.failed_runs == initial_failed + 1
        assert scheduler.metrics.anomalies_detected == 0  # No anomaly detected

    def test_update_symbol_specific_metrics(self, scheduler, sample_success_stats):
        """Test symbol-specific metrics are updated."""
        symbol_metrics = scheduler.metrics.symbol_stats["BTC-USD"]
        initial_runs = symbol_metrics.total_runs

        scheduler._update_metrics(sample_success_stats)

        assert symbol_metrics.total_runs == initial_runs + 1
        assert symbol_metrics.successful_runs == 1
        assert symbol_metrics.anomalies_detected == 1
        assert symbol_metrics.narratives_validated == 1
        assert symbol_metrics.last_run_time is not None

    def test_update_rejected_narrative_metrics(self, scheduler):
        """Test metrics for rejected narratives."""
        stats = PipelineStats(
            symbol="BTC-USD",
            success=True,
            phase_reached="complete",
            execution_time_seconds=2.0,
            anomaly_detected=True,
            news_count=5,
            cluster_count=1,
            narrative_validated=False,  # Rejected
            error_message=None,
        )

        scheduler._update_metrics(stats)

        assert scheduler.metrics.narratives_rejected == 1
        assert scheduler.metrics.narratives_validated == 0


class TestHandleError:
    """Tests for _handle_error method."""

    def test_error_handling(self, scheduler):
        """Test error handling updates metrics correctly."""
        error = Exception("Test error")
        symbol = "BTC-USD"

        scheduler._handle_error(symbol, error)

        assert scheduler.metrics.failed_runs == 1
        assert scheduler.metrics.symbol_stats[symbol].failed_runs == 1
        assert scheduler.metrics.symbol_stats[symbol].last_error == "Test error"
        assert scheduler.metrics.symbol_stats[symbol].last_run_time is not None


class TestGetMetrics:
    """Tests for get_metrics method."""

    def test_get_metrics_structure(self, scheduler):
        """Test metrics are returned in correct structure."""
        metrics = scheduler.get_metrics()

        assert "overall" in metrics
        assert "symbols" in metrics

        # Check overall metrics
        assert "total_runs" in metrics["overall"]
        assert "successful_runs" in metrics["overall"]
        assert "failed_runs" in metrics["overall"]
        assert "anomalies_detected" in metrics["overall"]

        # Check symbol metrics
        for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
            assert symbol in metrics["symbols"]
            assert "total_runs" in metrics["symbols"][symbol]
            assert "anomalies_detected" in metrics["symbols"][symbol]

    def test_get_metrics_serializable(self, scheduler, sample_success_stats):
        """Test metrics are JSON-serializable."""
        import json

        scheduler._update_metrics(sample_success_stats)
        metrics = scheduler.get_metrics()

        # Should not raise exception
        json_str = json.dumps(metrics)
        assert json_str is not None


class TestStorePricesCycle:
    """Tests for _store_prices_cycle method."""

    @pytest.mark.asyncio
    async def test_store_prices_success(self, scheduler):
        """Test price storage cycle succeeds."""
        mock_price_data = [
            Mock(symbol="BTC-USD"),
            Mock(symbol="ETH-USD"),
            Mock(symbol="SOL-USD"),
        ]

        scheduler.pipeline.crypto_client.get_prices = AsyncMock(
            return_value=mock_price_data
        )
        scheduler.pipeline.crypto_client.store_price = AsyncMock()

        with patch("src.orchestration.scheduler.get_db_context") as mock_db_context:
            mock_session = MagicMock()
            mock_db_context.return_value.__enter__.return_value = mock_session

            await scheduler._store_prices_cycle()

            # Verify prices fetched
            scheduler.pipeline.crypto_client.get_prices.assert_called_once_with(
                ["BTC-USD", "ETH-USD", "SOL-USD"]
            )

            # Verify store_price called for each symbol
            assert scheduler.pipeline.crypto_client.store_price.call_count == 3

    @pytest.mark.asyncio
    async def test_store_prices_partial_failure(self, scheduler):
        """Test price storage continues even if some symbols fail."""
        mock_price_data = [
            Mock(symbol="BTC-USD"),
            Mock(symbol="ETH-USD"),
        ]

        scheduler.pipeline.crypto_client.get_prices = AsyncMock(
            return_value=mock_price_data
        )

        # First call succeeds, second fails
        scheduler.pipeline.crypto_client.store_price = AsyncMock(
            side_effect=[None, Exception("DB error")]
        )

        with patch("src.orchestration.scheduler.get_db_context") as mock_db_context:
            mock_session = MagicMock()
            mock_db_context.return_value.__enter__.return_value = mock_session

            # Should not raise exception
            await scheduler._store_prices_cycle()

            # Verify both store attempts made
            assert scheduler.pipeline.crypto_client.store_price.call_count == 2


class TestRunDetectionCycle:
    """Tests for _run_detection_cycle method."""

    @pytest.mark.asyncio
    async def test_detection_cycle_success(self, scheduler, sample_success_stats):
        """Test detection cycle processes all symbols."""
        scheduler.pipeline.run_for_symbol = AsyncMock(
            return_value=(Mock(), sample_success_stats)
        )

        with patch("src.orchestration.scheduler.get_db_context") as mock_db_context:
            mock_session = MagicMock()
            mock_db_context.return_value.__enter__.return_value = mock_session

            await scheduler._run_detection_cycle()

            # Verify pipeline ran for each symbol
            assert scheduler.pipeline.run_for_symbol.call_count == 3

            # Verify metrics updated
            assert scheduler.metrics.last_run_time is not None
            assert scheduler.metrics.last_cycle_duration is not None

    @pytest.mark.asyncio
    async def test_detection_cycle_handles_symbol_failure(self, scheduler):
        """Test detection cycle continues when a symbol fails."""
        # First symbol succeeds, second fails, third succeeds
        scheduler.pipeline.run_for_symbol = AsyncMock(
            side_effect=[
                (Mock(), PipelineStats(
                    symbol="BTC-USD", success=True, phase_reached="complete",
                    execution_time_seconds=1.0, anomaly_detected=False,
                    news_count=0, cluster_count=0, narrative_validated=None,
                    error_message=None
                )),
                Exception("Pipeline error"),
                (Mock(), PipelineStats(
                    symbol="SOL-USD", success=True, phase_reached="complete",
                    execution_time_seconds=1.0, anomaly_detected=False,
                    news_count=0, cluster_count=0, narrative_validated=None,
                    error_message=None
                )),
            ]
        )

        with patch("src.orchestration.scheduler.get_db_context") as mock_db_context:
            mock_session = MagicMock()
            mock_db_context.return_value.__enter__.return_value = mock_session

            await scheduler._run_detection_cycle()

            # Verify all symbols attempted
            assert scheduler.pipeline.run_for_symbol.call_count == 3

            # Verify failure tracked
            assert scheduler.metrics.failed_runs > 0


class TestSchedulerMetrics:
    """Tests for SchedulerMetrics and SymbolMetrics dataclasses."""

    def test_scheduler_metrics_creation(self):
        """Test creating scheduler metrics."""
        metrics = SchedulerMetrics()

        assert metrics.total_runs == 0
        assert metrics.successful_runs == 0
        assert metrics.failed_runs == 0
        assert metrics.anomalies_detected == 0
        assert metrics.last_run_time is None
        assert isinstance(metrics.symbol_stats, dict)

    def test_symbol_metrics_creation(self):
        """Test creating symbol metrics."""
        metrics = SymbolMetrics()

        assert metrics.total_runs == 0
        assert metrics.successful_runs == 0
        assert metrics.failed_runs == 0
        assert metrics.anomalies_detected == 0
        assert metrics.narratives_validated == 0
        assert metrics.narratives_rejected == 0
        assert metrics.last_run_time is None
        assert metrics.last_error is None
