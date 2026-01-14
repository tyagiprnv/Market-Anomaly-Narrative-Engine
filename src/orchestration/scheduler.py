"""Scheduler for periodic anomaly detection across multiple symbols."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import Settings
from src.database.connection import get_db_context, init_database
from src.orchestration.pipeline import MarketAnomalyPipeline, PipelineStats

logger = logging.getLogger(__name__)


@dataclass
class SymbolMetrics:
    """Metrics for a single symbol."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    anomalies_detected: int = 0
    narratives_validated: int = 0
    narratives_rejected: int = 0
    last_run_time: datetime | None = None
    last_error: str | None = None


@dataclass
class SchedulerMetrics:
    """Aggregated metrics for the scheduler."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    anomalies_detected: int = 0
    narratives_validated: int = 0
    narratives_rejected: int = 0
    last_run_time: datetime | None = None
    last_cycle_duration: float | None = None
    symbol_stats: dict[str, SymbolMetrics] = field(default_factory=dict)


class AnomalyDetectionScheduler:
    """Schedules periodic anomaly detection across multiple symbols.

    This scheduler:
    1. Runs price storage job every 60 seconds (builds price history)
    2. Runs detection cycle periodically for all symbols
    3. Tracks metrics per symbol and overall
    4. Supports graceful start/stop
    """

    def __init__(self, settings: Settings):
        """Initialize the scheduler.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.pipeline = MarketAnomalyPipeline(settings)
        self.symbols = settings.detection.symbols
        self.poll_interval = settings.data_ingestion.poll_interval_seconds

        self.scheduler = AsyncIOScheduler()
        self.metrics = SchedulerMetrics()

        # Initialize symbol metrics
        for symbol in self.symbols:
            self.metrics.symbol_stats[symbol] = SymbolMetrics()

    async def start(self) -> None:
        """Start the scheduler.

        Initializes database connection and starts both:
        - Price storage job (every 60s)
        - Detection cycle job (every poll_interval seconds)
        """
        logger.info("Initializing database connection...")
        init_database(self.settings.database.url)

        logger.info("Starting scheduler...")

        # Add price storage job (runs every 60 seconds)
        self.scheduler.add_job(
            self._store_prices_cycle,
            "interval",
            seconds=60,
            max_instances=1,
            id="price_storage",
            name="Price Storage Cycle",
        )

        # Add detection cycle job
        self.scheduler.add_job(
            self._run_detection_cycle,
            "interval",
            seconds=self.poll_interval,
            max_instances=1,
            id="detection_cycle",
            name="Anomaly Detection Cycle",
        )

        # Start scheduler
        self.scheduler.start()

        logger.info(
            f"Scheduler started: monitoring {len(self.symbols)} symbols "
            f"every {self.poll_interval}s"
        )

    async def stop(self) -> None:
        """Stop the scheduler gracefully.

        Waits for current jobs to finish before shutdown.
        """
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    async def _store_prices_cycle(self) -> None:
        """Store current prices for all symbols.

        This builds the price history needed for anomaly detection.
        Runs independently of the detection cycle.
        """
        logger.debug(f"Starting price storage cycle for {len(self.symbols)} symbols")

        try:
            with get_db_context() as session:
                # Fetch current prices for all symbols
                prices = await self.pipeline.crypto_client.get_prices(self.symbols)

                # Store each price
                for price_data in prices:
                    try:
                        await self.pipeline.crypto_client.store_price(price_data, session)
                    except Exception as e:
                        logger.warning(
                            f"Failed to store price for {price_data.symbol}: {e}"
                        )

                logger.debug(f"Stored {len(prices)} price records")

        except Exception as e:
            logger.error(f"Price storage cycle failed: {e}", exc_info=True)

    async def _run_detection_cycle(self) -> None:
        """Run detection cycle for all symbols sequentially.

        Processes each symbol one at a time, tracking success/failure metrics.
        """
        cycle_start = datetime.utcnow()
        logger.info(f"Starting detection cycle for {len(self.symbols)} symbols")

        success_count = 0
        failure_count = 0
        anomaly_count = 0

        try:
            with get_db_context() as session:
                for symbol in self.symbols:
                    try:
                        # Run pipeline for symbol
                        anomaly, stats = await self.pipeline.run_for_symbol(
                            symbol, session
                        )

                        # Update metrics
                        self._update_metrics(stats)

                        # Log result
                        self._log_result(symbol, anomaly, stats)

                        # Update counters
                        if stats.success:
                            success_count += 1
                            if stats.anomaly_detected:
                                anomaly_count += 1
                        else:
                            failure_count += 1

                    except Exception as e:
                        logger.error(
                            f"Pipeline failed for {symbol}: {e}", exc_info=True
                        )
                        self._handle_error(symbol, e)
                        failure_count += 1

        except Exception as e:
            logger.error(f"Detection cycle failed: {e}", exc_info=True)

        finally:
            # Update cycle metrics
            cycle_end = datetime.utcnow()
            cycle_duration = (cycle_end - cycle_start).total_seconds()

            self.metrics.last_run_time = cycle_end
            self.metrics.last_cycle_duration = cycle_duration

            logger.info(
                f"Cycle complete: {success_count}/{len(self.symbols)} successful, "
                f"{anomaly_count} anomalies detected, duration={cycle_duration:.1f}s"
            )

            # Alert if high failure rate
            if failure_count > len(self.symbols) * 0.5:
                logger.critical(
                    f"High failure rate in cycle: {failure_count}/{len(self.symbols)} failed"
                )

    def _update_metrics(self, stats: PipelineStats) -> None:
        """Update metrics based on pipeline stats.

        Args:
            stats: Pipeline execution statistics
        """
        # Update overall metrics
        self.metrics.total_runs += 1
        if stats.success:
            self.metrics.successful_runs += 1
        else:
            self.metrics.failed_runs += 1

        if stats.anomaly_detected:
            self.metrics.anomalies_detected += 1

        if stats.narrative_validated is True:
            self.metrics.narratives_validated += 1
        elif stats.narrative_validated is False:
            self.metrics.narratives_rejected += 1

        # Update symbol-specific metrics
        symbol_metrics = self.metrics.symbol_stats[stats.symbol]
        symbol_metrics.total_runs += 1
        symbol_metrics.last_run_time = datetime.utcnow()

        if stats.success:
            symbol_metrics.successful_runs += 1
        else:
            symbol_metrics.failed_runs += 1
            symbol_metrics.last_error = stats.error_message

        if stats.anomaly_detected:
            symbol_metrics.anomalies_detected += 1

        if stats.narrative_validated is True:
            symbol_metrics.narratives_validated += 1
        elif stats.narrative_validated is False:
            symbol_metrics.narratives_rejected += 1

    def _log_result(
        self,
        symbol: str,
        anomaly: "Anomaly | None",
        stats: PipelineStats,
    ) -> None:
        """Log pipeline result.

        Args:
            symbol: Trading symbol
            anomaly: Detected anomaly (if any)
            stats: Pipeline statistics
        """
        if not stats.success:
            logger.warning(
                f"[{symbol}] Pipeline failed at phase '{stats.phase_reached}': "
                f"{stats.error_message}"
            )
        elif not stats.anomaly_detected:
            logger.debug(f"[{symbol}] No anomaly detected")
        else:
            logger.info(
                f"[{symbol}] Anomaly processed: "
                f"narrative_validated={stats.narrative_validated}, "
                f"news_count={stats.news_count}, "
                f"clusters={stats.cluster_count}"
            )

    def _handle_error(self, symbol: str, error: Exception) -> None:
        """Handle pipeline error.

        Args:
            symbol: Trading symbol
            error: Exception that occurred
        """
        symbol_metrics = self.metrics.symbol_stats[symbol]
        symbol_metrics.failed_runs += 1
        symbol_metrics.last_error = str(error)
        symbol_metrics.last_run_time = datetime.utcnow()

        self.metrics.failed_runs += 1

    def get_metrics(self) -> dict:
        """Get scheduler metrics as JSON-serializable dict.

        Returns:
            Dictionary with overall and per-symbol metrics
        """
        return {
            "overall": {
                "total_runs": self.metrics.total_runs,
                "successful_runs": self.metrics.successful_runs,
                "failed_runs": self.metrics.failed_runs,
                "anomalies_detected": self.metrics.anomalies_detected,
                "narratives_validated": self.metrics.narratives_validated,
                "narratives_rejected": self.metrics.narratives_rejected,
                "last_run_time": (
                    self.metrics.last_run_time.isoformat()
                    if self.metrics.last_run_time
                    else None
                ),
                "last_cycle_duration": self.metrics.last_cycle_duration,
            },
            "symbols": {
                symbol: {
                    "total_runs": metrics.total_runs,
                    "successful_runs": metrics.successful_runs,
                    "failed_runs": metrics.failed_runs,
                    "anomalies_detected": metrics.anomalies_detected,
                    "narratives_validated": metrics.narratives_validated,
                    "narratives_rejected": metrics.narratives_rejected,
                    "last_run_time": (
                        metrics.last_run_time.isoformat()
                        if metrics.last_run_time
                        else None
                    ),
                    "last_error": metrics.last_error,
                }
                for symbol, metrics in self.metrics.symbol_stats.items()
            },
        }
