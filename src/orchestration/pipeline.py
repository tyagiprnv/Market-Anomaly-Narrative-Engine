"""Pipeline orchestrator for Phase 1 → 2 → 3 anomaly detection and narrative generation."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from config.settings import Settings
from src.database.models import Anomaly, AnomalyTypeEnum, NewsArticle
from src.llm.client import LLMClient
from src.phase1_detector.anomaly_detection.models import DetectedAnomaly
from src.phase1_detector.anomaly_detection.statistical import AnomalyDetector
from src.phase1_detector.clustering.clustering import NewsClusterer
from src.phase1_detector.data_ingestion.binance_client import BinanceClient
from src.phase1_detector.data_ingestion.coinbase_client import CoinbaseClient
from src.phase1_detector.data_ingestion.crypto_client import CryptoClient
from src.phase1_detector.data_ingestion.models import PriceData
from src.phase1_detector.news_aggregation.aggregator import NewsAggregator
from src.phase1_detector.news_aggregation.models import NewsArticle as NewsArticlePydantic
from src.phase2_journalist.agent import JournalistAgent
from src.phase3_skeptic.validator import ValidationEngine

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Statistics for a single pipeline execution."""

    symbol: str
    success: bool
    phase_reached: str  # "detection", "news", "narrative", "validation", "complete"
    execution_time_seconds: float
    anomaly_detected: bool
    news_count: int
    cluster_count: int
    narrative_validated: bool | None
    error_message: str | None


class MarketAnomalyPipeline:
    """Orchestrates Phase 1 → 2 → 3 for a single symbol.

    This pipeline:
    1. Fetches price history from database
    2. Detects anomalies using statistical detectors (Phase 1)
    3. Fetches and clusters news articles (Phase 1)
    4. Generates narrative explaining anomaly (Phase 2)
    5. Validates narrative (Phase 3)
    """

    def __init__(self, settings: Settings, news_mode: str | None = None):
        """Initialize the pipeline with all components.

        Args:
            settings: Application settings
            news_mode: News aggregation mode ('live', 'replay', 'hybrid'). Defaults to settings.
        """
        self.settings = settings
        self.news_mode = news_mode or settings.news.mode

        # Initialize crypto client
        if settings.data_ingestion.primary_source == "coinbase":
            self.crypto_client: CryptoClient = CoinbaseClient(
                api_key=settings.data_ingestion.coinbase_api_key,
                api_secret=settings.data_ingestion.coinbase_api_secret,
            )
        else:
            self.crypto_client = BinanceClient(
                api_key=settings.data_ingestion.binance_api_key,
                api_secret=settings.data_ingestion.binance_api_secret,
            )

        # Initialize Phase 1 components
        self.detector = AnomalyDetector()
        self.news_aggregator = NewsAggregator(mode=self.news_mode)
        self.clusterer = NewsClusterer(settings)

        # Initialize Phase 2 component
        llm_client = LLMClient()
        # Note: JournalistAgent will be given a session in generate_narrative
        self.journalist = JournalistAgent(llm_client=llm_client)

        # Initialize Phase 3 component
        # Note: ValidationEngine will be given a session in _validate_narrative
        self.validator = ValidationEngine(llm_client=llm_client)

    async def run_for_symbol(
        self,
        symbol: str,
        session: Session,
    ) -> tuple[Anomaly | None, PipelineStats]:
        """Run full pipeline for a single symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC-USD')
            session: Database session

        Returns:
            Tuple of (anomaly with validated narrative, execution stats)
            Anomaly is None if no anomaly detected
        """
        start_time = datetime.utcnow()
        stats = PipelineStats(
            symbol=symbol,
            success=False,
            phase_reached="",
            execution_time_seconds=0.0,
            anomaly_detected=False,
            news_count=0,
            cluster_count=0,
            narrative_validated=None,
            error_message=None,
        )

        try:
            # Step 1: Check for duplicate anomaly
            logger.info(f"[{symbol}] Checking for duplicate anomaly...")
            duplicate = self._check_duplicate_anomaly(symbol, datetime.utcnow(), session)
            if duplicate:
                logger.info(
                    f"[{symbol}] Found recent duplicate anomaly (id={duplicate.id}), skipping"
                )
                stats.success = True
                stats.phase_reached = "duplicate_found"
                return duplicate, stats

            # Step 2: Fetch price history
            logger.info(f"[{symbol}] Fetching price history...")
            prices_df = await self._fetch_price_history(symbol, session)
            if prices_df is None or len(prices_df) < self.settings.orchestration.min_price_points:
                logger.info(
                    f"[{symbol}] Insufficient price history: {len(prices_df) if prices_df is not None else 0} points "
                    f"(need {self.settings.orchestration.min_price_points})"
                )
                stats.error_message = "Insufficient price history"
                return None, stats

            # Step 3: Detect anomaly (Phase 1)
            logger.info(f"[{symbol}] Running anomaly detection...")
            stats.phase_reached = "detection"
            detected_anomaly = await self._detect_anomaly(prices_df)

            if not detected_anomaly:
                logger.info(f"[{symbol}] No anomaly detected")
                stats.success = True
                stats.phase_reached = "detection_complete"
                return None, stats

            logger.info(
                f"[{symbol}] Anomaly detected: type={detected_anomaly.anomaly_type.value}, "
                f"confidence={detected_anomaly.confidence:.2f}, z_score={detected_anomaly.z_score:.2f}"
            )
            stats.anomaly_detected = True

            # Step 4: Persist anomaly
            logger.info(f"[{symbol}] Persisting anomaly to database...")
            anomaly = self._persist_anomaly(detected_anomaly, session)

            # Step 5: Fetch news (Phase 1)
            logger.info(f"[{symbol}] Fetching news articles...")
            stats.phase_reached = "news"
            try:
                news_articles = await self._fetch_and_persist_news(anomaly, session)
                stats.news_count = len(news_articles)
                logger.info(f"[{symbol}] Fetched {len(news_articles)} news articles")
            except Exception as e:
                logger.warning(f"[{symbol}] News fetch failed: {e}, continuing with empty news")
                news_articles = []
                stats.news_count = 0

            # Step 6: Cluster news (Phase 1)
            if news_articles:
                logger.info(f"[{symbol}] Clustering news articles...")
                try:
                    await self._cluster_news(anomaly.id, news_articles, session)
                    # Count clusters
                    anomaly_with_clusters = (
                        session.query(Anomaly)
                        .filter(Anomaly.id == anomaly.id)
                        .options(selectinload(Anomaly.news_clusters))
                        .first()
                    )
                    stats.cluster_count = len(anomaly_with_clusters.news_clusters)
                    logger.info(f"[{symbol}] Created {stats.cluster_count} news clusters")
                except Exception as e:
                    logger.warning(f"[{symbol}] Clustering failed: {e}, continuing without clusters")
                    stats.cluster_count = 0

            # Step 7: Generate narrative (Phase 2)
            logger.info(f"[{symbol}] Generating narrative...")
            stats.phase_reached = "narrative"
            narrative = await self._generate_narrative(anomaly.id, session)
            logger.info(f"[{symbol}] Narrative generated: '{narrative.narrative_text}'")

            # Step 8: Validate narrative (Phase 3)
            logger.info(f"[{symbol}] Validating narrative...")
            stats.phase_reached = "validation"
            validation_result = await self._validate_narrative(narrative.id, session)
            stats.narrative_validated = validation_result.validation_passed
            logger.info(
                f"[{symbol}] Validation complete: passed={validation_result.validation_passed}, "
                f"score={validation_result.aggregate_score:.2f}"
            )

            # Success!
            stats.success = True
            stats.phase_reached = "complete"

            # Reload anomaly with all relationships eagerly loaded
            from sqlalchemy.orm import joinedload
            final_anomaly = (
                session.query(Anomaly)
                .filter(Anomaly.id == anomaly.id)
                .options(
                    joinedload(Anomaly.narrative),  # Use joinedload for eager loading
                    selectinload(Anomaly.news_articles),
                    selectinload(Anomaly.news_clusters),
                )
                .first()
            )

            # Note: We could expunge objects to make them usable after session closes,
            # but for simplicity, we let the CLI handle the display within the session
            # or use the list-narratives command for viewing results
            return final_anomaly, stats

        except Exception as e:
            logger.error(f"[{symbol}] Pipeline failed: {e}", exc_info=True)
            stats.error_message = str(e)
            return None, stats

        finally:
            # Record execution time
            end_time = datetime.utcnow()
            stats.execution_time_seconds = (end_time - start_time).total_seconds()
            logger.info(
                f"[{symbol}] Pipeline complete: success={stats.success}, "
                f"phase={stats.phase_reached}, duration={stats.execution_time_seconds:.1f}s"
            )

    def _check_duplicate_anomaly(
        self,
        symbol: str,
        timestamp: datetime,
        session: Session,
    ) -> Anomaly | None:
        """Check for recent duplicate anomaly.

        Args:
            symbol: Trading pair symbol
            timestamp: Current timestamp
            session: Database session

        Returns:
            Existing anomaly if found within duplicate window, else None
        """
        cutoff_time = timestamp - timedelta(
            minutes=self.settings.orchestration.duplicate_window_minutes
        )

        # Query for recent anomaly
        recent_anomaly = (
            session.query(Anomaly)
            .filter(
                Anomaly.symbol == symbol,
                Anomaly.detected_at >= cutoff_time,
            )
            .order_by(Anomaly.detected_at.desc())
            .first()
        )

        return recent_anomaly

    async def _fetch_price_history(
        self,
        symbol: str,
        session: Session,
    ) -> pd.DataFrame | None:
        """Fetch price history from database.

        Args:
            symbol: Trading pair symbol
            session: Database session

        Returns:
            DataFrame with price history, or None if fetch fails
        """
        try:
            df = await self.crypto_client.get_price_history(
                symbol=symbol,
                minutes=self.settings.orchestration.price_history_lookback_minutes,
                session=session,
            )
            return df
        except Exception as e:
            logger.error(f"Failed to fetch price history for {symbol}: {e}")
            return None

    async def _detect_anomaly(self, prices_df: pd.DataFrame) -> DetectedAnomaly | None:
        """Run anomaly detection on price data.

        Args:
            prices_df: Price history DataFrame

        Returns:
            First detected anomaly (highest confidence), or None
        """
        # Run detection in thread executor (CPU-bound)
        anomalies = await asyncio.to_thread(self.detector.detect_all, prices_df)

        # Return first anomaly (highest confidence) or None
        return anomalies[0] if anomalies else None

    def _persist_anomaly(
        self,
        detected: DetectedAnomaly,
        session: Session,
    ) -> Anomaly:
        """Persist detected anomaly to database.

        Converts Pydantic DetectedAnomaly to SQLAlchemy Anomaly model.

        Args:
            detected: Detected anomaly (Pydantic)
            session: Database session

        Returns:
            Persisted Anomaly (SQLAlchemy ORM)
        """
        # Convert enum
        anomaly_type_enum = AnomalyTypeEnum[detected.anomaly_type.value.upper()]

        # Create ORM model
        anomaly = Anomaly(
            symbol=detected.symbol,
            detected_at=detected.detected_at,
            anomaly_type=anomaly_type_enum,
            z_score=detected.z_score,
            price_change_pct=detected.price_change_pct,
            volume_change_pct=detected.volume_change_pct,
            confidence=detected.confidence,
            baseline_window_minutes=detected.baseline_window_minutes,
            price_before=detected.price_before,
            price_at_detection=detected.price_at_detection,
            volume_before=detected.volume_before,
            volume_at_detection=detected.volume_at_detection,
        )

        session.add(anomaly)
        session.commit()
        session.refresh(anomaly)

        return anomaly

    async def _fetch_and_persist_news(
        self,
        anomaly: Anomaly,
        session: Session,
    ) -> list[NewsArticle]:
        """Fetch news and persist to database.

        Args:
            anomaly: Anomaly to fetch news for
            session: Database session

        Returns:
            List of persisted NewsArticle ORM models
        """
        # Fetch news (returns Pydantic models)
        news_pydantic = await self.news_aggregator.get_news_for_anomaly(
            symbols=[anomaly.symbol],
            anomaly_time=anomaly.detected_at,
            window_minutes=self.settings.detection.news_window_minutes,
        )

        if not news_pydantic:
            return []

        # Convert to ORM models and persist
        news_articles = []
        for news in news_pydantic:
            article = NewsArticle(
                anomaly_id=anomaly.id,
                source=news.source,
                title=news.title,
                url=news.url,
                published_at=news.published_at,
                summary=news.summary,
                sentiment=news.sentiment,
                symbols=news.symbols,
                timing_tag=news.timing_tag,
                time_diff_minutes=news.time_diff_minutes,
                cluster_id=-1,  # Not clustered yet
            )
            session.add(article)
            news_articles.append(article)

        session.commit()

        # Refresh to get IDs
        for article in news_articles:
            session.refresh(article)

        return news_articles

    async def _cluster_news(
        self,
        anomaly_id: str,
        articles: Sequence[NewsArticle],
        session: Session,
    ) -> None:
        """Cluster news articles.

        Args:
            anomaly_id: Anomaly ID
            articles: News articles to cluster
            session: Database session
        """
        # Convert ORM to Pydantic for clusterer
        articles_pydantic = [
            NewsArticlePydantic(
                source=a.source,
                title=a.title,
                url=a.url,
                published_at=a.published_at,
                summary=a.summary,
                sentiment=a.sentiment,
                symbols=a.symbols,
                timing_tag=a.timing_tag,
                time_diff_minutes=a.time_diff_minutes,
            )
            for a in articles
        ]

        # Run clustering in thread executor (CPU-bound)
        await asyncio.to_thread(
            self.clusterer.cluster_and_persist,
            anomaly_id,
            articles_pydantic,
            session,
        )

    async def _generate_narrative(
        self,
        anomaly_id: str,
        session: Session,
    ) -> "Narrative":
        """Generate narrative for anomaly.

        Args:
            anomaly_id: Anomaly ID
            session: Database session

        Returns:
            Generated Narrative (with fallback if generation fails)
        """
        # Reload anomaly with news articles
        anomaly = (
            session.query(Anomaly)
            .filter(Anomaly.id == anomaly_id)
            .options(selectinload(Anomaly.news_articles))
            .first()
        )

        # Set session on journalist for this generation
        self.journalist.session = session
        from src.phase2_journalist.tools import ToolRegistry
        self.journalist.tool_registry = ToolRegistry(session=session)

        # Generate narrative (Phase 2) - pass news articles, not session
        narrative = await self.journalist.generate_narrative(anomaly, anomaly.news_articles)

        return narrative

    async def _validate_narrative(
        self,
        narrative_id: str,
        session: Session,
    ) -> "ValidationResult":
        """Validate narrative.

        Args:
            narrative_id: Narrative ID
            session: Database session

        Returns:
            ValidationResult
        """
        from src.database.models import Narrative

        # Reload narrative with all relationships
        narrative = (
            session.query(Narrative)
            .filter(Narrative.id == narrative_id)
            .options(
                selectinload(Narrative.anomaly).selectinload(Anomaly.news_articles),
                selectinload(Narrative.anomaly).selectinload(Anomaly.news_clusters),
            )
            .first()
        )

        # Set session on validator for this validation
        self.validator.session = session
        from src.phase3_skeptic.validators import ValidatorRegistry
        self.validator.validator_registry = ValidatorRegistry(
            session=session,
            llm_client=self.validator.llm_client
        )

        # Validate (Phase 3)
        result = await self.validator.validate_narrative(narrative)

        return result
