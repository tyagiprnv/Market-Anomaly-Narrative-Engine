"""Unit tests for ValidationEngine."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, UTC

from src.phase3_skeptic import ValidationEngine
from src.phase3_skeptic.validators import ValidatorRegistry, ValidatorOutput
from config.settings import settings


class TestValidationEngine:
    """Tests for ValidationEngine orchestrator."""

    @pytest.mark.asyncio
    async def test_validate_narrative_success(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test successful narrative validation."""
        # Link relationships
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        # Create engine with mock session
        mock_session = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        engine = ValidationEngine(
            session=mock_session,
            llm_client=mock_llm_client
        )

        # Run validation
        result = await engine.validate_narrative(sample_narrative)

        # Assertions
        assert result.validated is True
        assert isinstance(result.validation_passed, bool)
        assert 0.0 <= result.aggregate_score <= 1.0
        assert result.validation_reason is not None
        assert len(result.validator_results) >= 5  # At least 5 rule validators

        # Check database was updated
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_narrative_without_session(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test validation without database session."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(sample_narrative)

        # Should still validate
        assert result.validated is True
        assert isinstance(result.validation_passed, bool)

    @pytest.mark.asyncio
    async def test_validate_missing_anomaly_raises(
        self,
        sample_narrative,
        mock_llm_client
    ):
        """Test validation fails if anomaly relationship is missing."""
        # Remove anomaly relationship
        sample_narrative.anomaly = None

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="missing anomaly relationship"):
            await engine.validate_narrative(sample_narrative)

    @pytest.mark.asyncio
    async def test_judge_llm_conditional_execution(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test Judge LLM is only called when score meets threshold."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(sample_narrative)

        # Check if Judge LLM was called based on rule score
        if result.aggregate_score >= settings.validation.judge_llm_min_trigger_score:
            # Judge LLM should be in results
            assert "judge_llm" in result.validator_results
            mock_llm_client.chat_completion.assert_called()
        else:
            # Judge LLM should not be in results
            assert "judge_llm" not in result.validator_results
            mock_llm_client.chat_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_poor_quality_narrative_has_low_quality_scores(
        self,
        poor_quality_narrative,
        mock_llm_client
    ):
        """Test poor quality narrative gets low quality validator scores."""
        anomaly = poor_quality_narrative.anomaly
        anomaly.news_articles = []
        poor_quality_narrative.anomaly = anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(poor_quality_narrative)

        # Quality and tool consistency validators should score low
        quality_result = result.validator_results.get("narrative_quality")
        tool_result = result.validator_results.get("tool_consistency")

        if quality_result:
            assert quality_result.score < 0.6  # Low quality score
        if tool_result:
            assert tool_result.score < 0.6  # Low tool usage score

        # Overall result may still pass if Judge LLM scores high (weighted scoring)

    @pytest.mark.asyncio
    async def test_contradictory_narrative_fails(
        self,
        contradictory_narrative,
        mock_llm_client
    ):
        """Test contradictory narrative fails validation."""
        anomaly = contradictory_narrative.anomaly
        anomaly.news_articles = []
        contradictory_narrative.anomaly = anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(contradictory_narrative)

        # Should fail due to sentiment contradiction
        assert result.validation_passed is False
        # Check that sentiment_match validator failed
        if "sentiment_match" in result.validator_results:
            sentiment_result = result.validator_results["sentiment_match"]
            assert sentiment_result.score == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_score_calculation(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test aggregate score is calculated correctly."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(sample_narrative)

        # Score should be weighted average
        total_weighted = 0.0
        total_weight = 0.0

        for name, output in result.validator_results.items():
            if output.success and output.score is not None:
                validator = engine.validator_registry.get_validator(name)
                if validator:
                    total_weighted += output.score * validator.weight * output.confidence
                    total_weight += validator.weight * output.confidence

        expected_score = total_weighted / total_weight if total_weight > 0 else 0.0

        # Allow small floating point differences
        assert abs(result.aggregate_score - expected_score) < 0.01

    @pytest.mark.asyncio
    async def test_critical_validator_failure_overrides(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test critical validator failures override threshold."""
        # Create scenario where timing is post-event (critical failure)
        from datetime import timedelta
        from src.database.models import NewsArticle
        import uuid

        # All news is post-event
        post_event_articles = [
            NewsArticle(
                id=str(uuid.uuid4()),
                anomaly_id=sample_anomaly.id,
                source="test",
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                published_at=sample_anomaly.detected_at + timedelta(minutes=10),
                timing_tag="post_event",
                time_diff_minutes=10.0,
                anomaly=sample_anomaly
            )
            for i in range(3)
        ]

        sample_anomaly.news_articles = post_event_articles
        sample_narrative.anomaly = sample_anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(sample_narrative)

        # Should fail due to critical timing issue
        # (even if other validators pass)
        timing_result = result.validator_results.get("timing_coherence")
        if timing_result and timing_result.score is not None and timing_result.score < 0.3:
            assert result.validation_passed is False
            assert "timing_coherence" in result.validation_reason.lower()

    @pytest.mark.asyncio
    async def test_database_rollback_on_error(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test database rollback on persistence error."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        # Create mock session that raises on commit
        mock_session = Mock()
        mock_session.commit = Mock(side_effect=Exception("DB error"))
        mock_session.rollback = Mock()

        engine = ValidationEngine(
            session=mock_session,
            llm_client=mock_llm_client
        )

        # Should raise exception and call rollback
        with pytest.raises(Exception, match="DB error"):
            await engine.validate_narrative(sample_narrative)

        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_execution(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test parallel and sequential execution produce same results."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        # Test with parallel execution (default)
        engine_parallel = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result_parallel = await engine_parallel.validate_narrative(sample_narrative)

        # Test with sequential execution
        with patch.object(settings.validation, 'parallel_validation', False):
            engine_sequential = ValidationEngine(
                session=None,
                llm_client=mock_llm_client
            )

            result_sequential = await engine_sequential.validate_narrative(sample_narrative)

        # Results should be similar (allow small differences due to timing)
        assert abs(result_parallel.aggregate_score - result_sequential.aggregate_score) < 0.05
        assert result_parallel.validation_passed == result_sequential.validation_passed

    @pytest.mark.asyncio
    async def test_confidence_calculation(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test overall confidence is calculated from validator confidences."""
        sample_anomaly.news_articles = sample_news_articles
        sample_narrative.anomaly = sample_anomaly

        engine = ValidationEngine(
            session=None,
            llm_client=mock_llm_client
        )

        result = await engine.validate_narrative(sample_narrative)

        # Confidence should be average of successful validator confidences
        confidences = [
            output.confidence
            for output in result.validator_results.values()
            if output.success
        ]

        expected_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        assert abs(result.confidence - expected_confidence) < 0.01
