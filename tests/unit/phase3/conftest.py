"""Pytest fixtures for Phase 3 validation tests."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, AsyncMock
import uuid

from src.database.models import Narrative, Anomaly, NewsArticle, NewsCluster, AnomalyTypeEnum
from src.phase3_skeptic.validators.models import ValidationContext
from src.llm.client import LLMClient
from src.llm.models import LLMResponse, LLMRole, TokenUsage


@pytest.fixture
def sample_anomaly():
    """Create a sample anomaly for testing."""
    return Anomaly(
        id=str(uuid.uuid4()),
        symbol="BTC-USD",
        detected_at=datetime.now(UTC),
        anomaly_type=AnomalyTypeEnum.PRICE_SPIKE,
        z_score=4.5,
        price_change_pct=8.5,
        volume_change_pct=15.2,
        confidence=0.92,
        baseline_window_minutes=60,
        price_before=45000.0,
        price_at_detection=48825.0,
        volume_before=1000000.0,
        volume_at_detection=1152000.0,
        news_articles=[],
        news_clusters=[]
    )


@pytest.fixture
def sample_narrative(sample_anomaly):
    """Create a sample narrative for testing."""
    narrative = Narrative(
        id=str(uuid.uuid4()),
        anomaly_id=sample_anomaly.id,
        narrative_text=(
            "Bitcoin surged 8.5% following positive regulatory news from the SEC. "
            "The announcement clarified the legal status of cryptocurrency exchanges, "
            "boosting investor confidence."
        ),
        confidence_score=0.85,
        tools_used=["verify_timestamp", "sentiment_check", "market_context"],
        tool_results={
            "verify_timestamp": {
                "verified": True,
                "pre_event_count": 3,
                "post_event_count": 1
            },
            "sentiment_check": {
                "sentiment": 0.75,
                "confidence": 0.9
            },
            "market_context": {
                "trend": "bullish",
                "volatility": "moderate"
            }
        },
        validated=False,
        validation_passed=None,
        validation_reason=None,
        llm_provider="anthropic",
        llm_model="claude-3-5-haiku-20241022",
        generation_time_seconds=2.5,
        anomaly=sample_anomaly
    )
    return narrative


@pytest.fixture
def sample_news_articles(sample_anomaly):
    """Create sample news articles for testing."""
    base_time = sample_anomaly.detected_at
    return [
        NewsArticle(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            source="cryptopanic",
            title="SEC Announces New Crypto Exchange Guidelines",
            url="https://example.com/news1",
            published_at=base_time - timedelta(minutes=15),
            summary="The SEC has released comprehensive guidelines...",
            cluster_id=0,
            timing_tag="pre_event",
            time_diff_minutes=-15.0,
            anomaly=sample_anomaly
        ),
        NewsArticle(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            source="reddit",
            title="Positive SEC News Boosts Crypto Market",
            url="https://reddit.com/r/bitcoin/post123",
            published_at=base_time - timedelta(minutes=10),
            summary="Major regulatory clarity from the SEC...",
            cluster_id=0,
            timing_tag="pre_event",
            time_diff_minutes=-10.0,
            anomaly=sample_anomaly
        ),
        NewsArticle(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            source="newsapi",
            title="Bitcoin Reaches New High After SEC Announcement",
            url="https://example.com/news2",
            published_at=base_time + timedelta(minutes=5),
            summary="Bitcoin prices surged following...",
            cluster_id=1,
            timing_tag="post_event",
            time_diff_minutes=5.0,
            anomaly=sample_anomaly
        ),
    ]


@pytest.fixture
def sample_news_clusters(sample_anomaly):
    """Create sample news clusters for testing."""
    return [
        NewsCluster(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            cluster_number=0,
            article_ids=["article1", "article2"],
            centroid_summary="SEC regulatory announcement",
            dominant_sentiment=0.7,
            size=2,
            anomaly=sample_anomaly
        )
    ]


@pytest.fixture
def validation_context(sample_narrative, sample_anomaly, sample_news_articles, sample_news_clusters):
    """Create a complete validation context for testing."""
    # Link articles to anomaly
    sample_anomaly.news_articles = sample_news_articles
    sample_anomaly.news_clusters = sample_news_clusters

    return ValidationContext(
        narrative=sample_narrative,
        anomaly=sample_anomaly,
        news_articles=sample_news_articles,
        news_clusters=sample_news_clusters
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    client = Mock(spec=LLMClient)

    # Mock chat_completion to return a valid response
    async def mock_chat_completion(*args, **kwargs):
        return LLMResponse(
            id="test-response-id",
            content='{"plausibility": 4, "causality": 5, "coherence": 4, "reasoning": "Strong causal link with good timing"}',
            role=LLMRole.ASSISTANT,
            tool_calls=None,
            finish_reason="stop",
            model="claude-3-5-haiku-20241022",
            usage=TokenUsage(
                prompt_tokens=500,
                completion_tokens=100,
                total_tokens=600
            )
        )

    client.chat_completion = AsyncMock(side_effect=mock_chat_completion)
    return client


@pytest.fixture
def negative_sentiment_narrative(sample_anomaly):
    """Create a narrative with negative sentiment for testing mismatches."""
    anomaly_drop = Anomaly(
        id=str(uuid.uuid4()),
        symbol="BTC-USD",
        detected_at=datetime.now(UTC),
        anomaly_type=AnomalyTypeEnum.PRICE_DROP,
        z_score=-4.2,
        price_change_pct=-7.5,
        volume_change_pct=12.0,
        confidence=0.88,
        baseline_window_minutes=60,
        price_before=48000.0,
        price_at_detection=44400.0,
        volume_before=1000000.0,
        volume_at_detection=1120000.0,
        news_articles=[],
        news_clusters=[]
    )

    narrative = Narrative(
        id=str(uuid.uuid4()),
        anomaly_id=anomaly_drop.id,
        narrative_text=(
            "Bitcoin plummeted 7.5% amid fears of stricter regulation. "
            "Negative market sentiment drove heavy selling pressure."
        ),
        confidence_score=0.80,
        tools_used=["sentiment_check"],
        tool_results={
            "sentiment_check": {
                "sentiment": -0.65,
                "confidence": 0.85
            }
        },
        validated=False,
        llm_provider="anthropic",
        llm_model="claude-3-5-haiku-20241022",
        anomaly=anomaly_drop
    )
    return narrative


@pytest.fixture
def contradictory_narrative(sample_anomaly):
    """Create a narrative with contradictory sentiment for testing failures."""
    # Price spike with negative sentiment (contradiction)
    narrative = Narrative(
        id=str(uuid.uuid4()),
        anomaly_id=sample_anomaly.id,
        narrative_text="Bitcoin crashed following negative regulatory news.",
        confidence_score=0.60,
        tools_used=["sentiment_check"],
        tool_results={
            "sentiment_check": {
                "sentiment": -0.70,  # Negative sentiment
                "confidence": 0.85
            }
        },
        validated=False,
        llm_provider="anthropic",
        llm_model="claude-3-5-haiku-20241022",
        anomaly=sample_anomaly  # Price SPIKE anomaly
    )
    return narrative


@pytest.fixture
def poor_quality_narrative(sample_anomaly):
    """Create a narrative with quality issues for testing."""
    narrative = Narrative(
        id=str(uuid.uuid4()),
        anomaly_id=sample_anomaly.id,
        narrative_text=(
            "Bitcoin possibly might have increased due to unclear reasons. "
            "The market could potentially be influenced by various factors. "
            "However, it's unclear what exactly happened."
        ),  # 3 sentences (too many), lots of hedging
        confidence_score=0.50,
        tools_used=[],  # No tools used
        tool_results={},
        validated=False,
        llm_provider="anthropic",
        llm_model="claude-3-5-haiku-20241022",
        anomaly=sample_anomaly
    )
    return narrative
