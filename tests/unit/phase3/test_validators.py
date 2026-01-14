"""Unit tests for individual validators."""

import pytest
from datetime import datetime, UTC

from src.phase3_skeptic.validators import (
    SentimentMatchValidator,
    TimingCoherenceValidator,
    MagnitudeCoherenceValidator,
    ToolConsistencyValidator,
    NarrativeQualityValidator,
)
from src.database.models import AnomalyTypeEnum


class TestSentimentMatchValidator:
    """Tests for SentimentMatchValidator."""

    @pytest.mark.asyncio
    async def test_positive_sentiment_with_spike(self, sample_narrative, sample_anomaly, sample_news_articles):
        """Test positive sentiment aligns with price spike."""
        validator = SentimentMatchValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        assert result.success is True
        assert result.passed is True
        assert result.score == 1.0
        assert "aligns with price spike" in result.reasoning

    @pytest.mark.asyncio
    async def test_negative_sentiment_with_drop(self, negative_sentiment_narrative):
        """Test negative sentiment aligns with price drop."""
        validator = SentimentMatchValidator()
        anomaly = negative_sentiment_narrative.anomaly

        result = await validator.validate(
            negative_sentiment_narrative,
            anomaly,
            []
        )

        assert result.success is True
        assert result.passed is True
        assert result.score == 1.0
        assert "aligns with price drop" in result.reasoning

    @pytest.mark.asyncio
    async def test_contradictory_sentiment(self, contradictory_narrative):
        """Test contradictory sentiment fails validation."""
        validator = SentimentMatchValidator()
        anomaly = contradictory_narrative.anomaly

        result = await validator.validate(
            contradictory_narrative,
            anomaly,
            []
        )

        assert result.success is True
        assert result.passed is False
        assert result.score == 0.0
        assert "contradicts" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_missing_sentiment_data(self, sample_narrative, sample_anomaly, sample_news_articles):
        """Test handling of missing sentiment data."""
        # Remove sentiment data
        sample_narrative.tool_results = {}

        validator = SentimentMatchValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        assert result.success is True
        assert result.score == 0.5
        assert "No sentiment data" in result.reasoning


class TestTimingCoherenceValidator:
    """Tests for TimingCoherenceValidator."""

    @pytest.mark.asyncio
    async def test_all_pre_event_news(self, sample_narrative, sample_anomaly):
        """Test all pre-event news gets perfect score."""
        # Create news with all pre-event timing
        from datetime import timedelta
        from src.database.models import NewsArticle
        import uuid

        pre_event_articles = [
            NewsArticle(
                id=str(uuid.uuid4()),
                anomaly_id=sample_anomaly.id,
                source="test",
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                published_at=sample_anomaly.detected_at - timedelta(minutes=10+i),
                timing_tag="pre_event",
                time_diff_minutes=-(10+i),
                anomaly=sample_anomaly
            )
            for i in range(3)
        ]

        validator = TimingCoherenceValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            pre_event_articles
        )

        assert result.success is True
        assert result.passed is True
        assert result.score == 1.0
        assert "All 3 news articles occurred before" in result.reasoning

    @pytest.mark.asyncio
    async def test_post_event_news_fails(self, sample_narrative, sample_anomaly):
        """Test majority post-event news fails validation."""
        from datetime import timedelta
        from src.database.models import NewsArticle
        import uuid

        post_event_articles = [
            NewsArticle(
                id=str(uuid.uuid4()),
                anomaly_id=sample_anomaly.id,
                source="test",
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                published_at=sample_anomaly.detected_at + timedelta(minutes=5+i),
                timing_tag="post_event",
                time_diff_minutes=5+i,
                anomaly=sample_anomaly
            )
            for i in range(3)
        ]

        validator = TimingCoherenceValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            post_event_articles
        )

        assert result.success is True
        assert result.passed is False
        assert result.score == 0.2
        assert "post-event" in result.reasoning

    @pytest.mark.asyncio
    async def test_no_news_articles(self, sample_narrative, sample_anomaly):
        """Test handling of no news articles."""
        validator = TimingCoherenceValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            []
        )

        assert result.success is True
        assert result.score == 0.5
        assert "No news articles" in result.reasoning


class TestMagnitudeCoherenceValidator:
    """Tests for MagnitudeCoherenceValidator."""

    @pytest.mark.asyncio
    async def test_large_magnitude_with_strong_language(self, sample_anomaly):
        """Test large magnitude with appropriate strong language."""
        from src.database.models import Narrative
        import uuid

        # Create narrative with strong language
        narrative = Narrative(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            narrative_text="Bitcoin surged dramatically as prices skyrocketed.",
            confidence_score=0.9,
            tools_used=[],
            tool_results={},
            validated=False,
            llm_provider="test",
            llm_model="test",
            anomaly=sample_anomaly
        )

        # Increase z-score to large
        sample_anomaly.z_score = 6.0
        sample_anomaly.price_change_pct = 12.0

        validator = MagnitudeCoherenceValidator()
        result = await validator.validate(narrative, sample_anomaly, [])

        assert result.success is True
        assert result.passed is True
        assert result.score == 1.0
        assert "Strong language matches large magnitude" in result.reasoning

    @pytest.mark.asyncio
    async def test_small_magnitude_with_exaggerated_language(self, sample_anomaly):
        """Test small magnitude with exaggerated language fails."""
        from src.database.models import Narrative
        import uuid

        # Create narrative with exaggerated language
        narrative = Narrative(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            narrative_text="Bitcoin crashed and plummeted dramatically.",
            confidence_score=0.7,
            tools_used=[],
            tool_results={},
            validated=False,
            llm_provider="test",
            llm_model="test",
            anomaly=sample_anomaly
        )

        # Set small z-score
        sample_anomaly.z_score = 2.0
        sample_anomaly.price_change_pct = 2.5

        validator = MagnitudeCoherenceValidator()
        result = await validator.validate(narrative, sample_anomaly, [])

        assert result.success is True
        assert result.score == 0.3
        assert "Exaggerated" in result.reasoning

    @pytest.mark.asyncio
    async def test_neutral_language_acceptable(self, sample_anomaly):
        """Test neutral language is acceptable for any magnitude."""
        from src.database.models import Narrative
        import uuid

        narrative = Narrative(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            narrative_text="Bitcoin price changed due to market factors.",
            confidence_score=0.8,
            tools_used=[],
            tool_results={},
            validated=False,
            llm_provider="test",
            llm_model="test",
            anomaly=sample_anomaly
        )

        validator = MagnitudeCoherenceValidator()
        result = await validator.validate(narrative, sample_anomaly, [])

        assert result.success is True
        assert result.score == 0.7
        assert "Neutral language" in result.reasoning


class TestToolConsistencyValidator:
    """Tests for ToolConsistencyValidator."""

    @pytest.mark.asyncio
    async def test_sufficient_tools_used(self, sample_narrative, sample_anomaly, sample_news_articles):
        """Test narrative with sufficient tools passes."""
        validator = ToolConsistencyValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        assert result.success is True
        assert result.passed is True
        assert result.score >= 0.9
        assert "consistent" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_no_tools_used_fails(self, poor_quality_narrative):
        """Test narrative with no tools fails."""
        validator = ToolConsistencyValidator()
        anomaly = poor_quality_narrative.anomaly

        result = await validator.validate(
            poor_quality_narrative,
            anomaly,
            []
        )

        assert result.success is True
        assert result.passed is False
        assert result.score == 0.4
        assert "No tools were used" in result.reasoning

    @pytest.mark.asyncio
    async def test_contradictory_tools(self, sample_anomaly):
        """Test contradictory tool results are detected."""
        from src.database.models import Narrative
        import uuid

        # Create narrative with contradictory tool results
        narrative = Narrative(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            narrative_text="Test narrative",
            confidence_score=0.7,
            tools_used=["sentiment_check", "market_context"],
            tool_results={
                "sentiment_check": {"sentiment": 0.8},  # Positive
                "market_context": {"trend": "bearish"}  # Bearish
            },
            validated=False,
            llm_provider="test",
            llm_model="test",
            anomaly=sample_anomaly
        )

        validator = ToolConsistencyValidator()
        result = await validator.validate(narrative, sample_anomaly, [])

        assert result.success is True
        # Should detect contradiction
        assert result.metadata["contradictions_found"] > 0


class TestNarrativeQualityValidator:
    """Tests for NarrativeQualityValidator."""

    @pytest.mark.asyncio
    async def test_perfect_quality(self, sample_narrative, sample_anomaly, sample_news_articles):
        """Test perfectly formatted narrative passes."""
        validator = NarrativeQualityValidator()
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        assert result.success is True
        assert result.passed is True
        # Should have high score (exact 1.0 depends on sentence count)
        assert result.score >= 0.7

    @pytest.mark.asyncio
    async def test_hedging_language_penalized(self, poor_quality_narrative):
        """Test hedging language is penalized."""
        validator = NarrativeQualityValidator()
        anomaly = poor_quality_narrative.anomaly

        result = await validator.validate(
            poor_quality_narrative,
            anomaly,
            []
        )

        assert result.success is True
        assert result.score < 0.8
        assert "hedging" in result.reasoning.lower() or "sentences" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_unknown_fallback_detected(self, sample_anomaly):
        """Test 'Unknown' fallback is detected."""
        from src.database.models import Narrative
        import uuid

        narrative = Narrative(
            id=str(uuid.uuid4()),
            anomaly_id=sample_anomaly.id,
            narrative_text="Unknown cause of price movement.",
            confidence_score=0.5,
            tools_used=[],
            tool_results={},
            validated=False,
            llm_provider="test",
            llm_model="test",
            anomaly=sample_anomaly
        )

        validator = NarrativeQualityValidator()
        result = await validator.validate(narrative, sample_anomaly, [])

        assert result.success is True
        assert result.passed is False
        assert result.score == 0.5
        assert "Unknown" in result.reasoning
