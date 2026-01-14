"""Unit tests for ValidatorRegistry and JudgeLLMValidator."""

import pytest
from unittest.mock import Mock, AsyncMock
import json

from src.phase3_skeptic.validators import ValidatorRegistry, JudgeLLMValidator, ValidatorOutput
from src.llm.models import LLMResponse, LLMRole, TokenUsage
from config.settings import settings


class TestValidatorRegistry:
    """Tests for ValidatorRegistry."""

    def test_registry_initialization(self, mock_llm_client):
        """Test registry initializes with all validators."""
        registry = ValidatorRegistry(
            session=None,
            llm_client=mock_llm_client
        )

        all_validators = registry.get_all_validators()

        # Should have at least 5 rule validators
        assert len(all_validators) >= 5

        # Check expected validators are registered
        assert "sentiment_match" in all_validators
        assert "timing_coherence" in all_validators
        assert "magnitude_coherence" in all_validators
        assert "tool_consistency" in all_validators
        assert "narrative_quality" in all_validators

        # Judge LLM should be present if enabled
        if settings.validation.judge_llm_enabled:
            assert "judge_llm" in all_validators

    def test_get_rule_validators(self, mock_llm_client):
        """Test getting only rule validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        rule_validators = registry.get_rule_validators()

        # Should have exactly 5 rule validators
        assert len(rule_validators) == 5
        assert "judge_llm" not in rule_validators

    def test_get_llm_validators(self, mock_llm_client):
        """Test getting only LLM validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        llm_validators = registry.get_llm_validators()

        if settings.validation.judge_llm_enabled:
            assert "judge_llm" in llm_validators
            assert len(llm_validators) == 1
        else:
            assert len(llm_validators) == 0

    def test_get_validator_by_name(self, mock_llm_client):
        """Test retrieving validator by name."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        validator = registry.get_validator("sentiment_match")
        assert validator is not None
        assert validator.name == "sentiment_match"

        # Non-existent validator
        invalid = registry.get_validator("nonexistent")
        assert invalid is None

    @pytest.mark.asyncio
    async def test_validate_rules_only_parallel(self, validation_context, mock_llm_client):
        """Test parallel execution of rule validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        results = await registry.validate_rules_only(
            validation_context,
            parallel=True
        )

        # Should have 5 rule validators
        assert len(results) == 5
        assert all(isinstance(r, ValidatorOutput) for r in results.values())

        # All should have executed successfully
        assert all(r.success for r in results.values())

    @pytest.mark.asyncio
    async def test_validate_rules_only_sequential(self, validation_context, mock_llm_client):
        """Test sequential execution of rule validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        results = await registry.validate_rules_only(
            validation_context,
            parallel=False
        )

        # Should have same results as parallel
        assert len(results) == 5
        assert all(isinstance(r, ValidatorOutput) for r in results.values())

    @pytest.mark.asyncio
    async def test_validate_all_includes_llm(self, validation_context, mock_llm_client):
        """Test validate_all includes LLM validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        results = await registry.validate_all(
            validation_context,
            parallel=True,
            include_llm=True
        )

        # Should include both rule and LLM validators
        assert len(results) >= 5

        if settings.validation.judge_llm_enabled:
            assert "judge_llm" in results

    @pytest.mark.asyncio
    async def test_validate_all_excludes_llm(self, validation_context, mock_llm_client):
        """Test validate_all can exclude LLM validators."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        results = await registry.validate_all(
            validation_context,
            parallel=True,
            include_llm=False
        )

        # Should only have rule validators
        assert len(results) == 5
        assert "judge_llm" not in results

    @pytest.mark.asyncio
    async def test_error_isolation(self, validation_context, mock_llm_client):
        """Test validator errors are isolated and don't crash registry."""
        # Create a validator that will fail
        from src.phase3_skeptic.validators.base import Validator

        class FailingValidator(Validator):
            name = "failing_test"
            description = "Test validator that always fails"
            weight = 1.0

            async def validate(self, narrative, anomaly, news_articles, **kwargs):
                raise Exception("Intentional test failure")

        registry = ValidatorRegistry(llm_client=mock_llm_client)

        # Manually add failing validator
        registry._validators["failing_test"] = FailingValidator()
        registry._rule_validators["failing_test"] = FailingValidator()

        # Should not crash
        results = await registry.validate_rules_only(
            validation_context,
            parallel=True
        )

        # Failing validator should have error output
        assert "failing_test" in results
        failing_result = results["failing_test"]
        assert failing_result.success is False
        assert failing_result.error is not None

        # Other validators should still work
        assert results["sentiment_match"].success is True

    def test_get_validator_info(self, mock_llm_client):
        """Test getting validator metadata."""
        registry = ValidatorRegistry(llm_client=mock_llm_client)

        info = registry.get_validator_info()

        # Should have info for all validators
        assert len(info) >= 5

        # Check info structure
        for name, metadata in info.items():
            assert "name" in metadata
            assert "description" in metadata
            assert "weight" in metadata
            assert isinstance(metadata["weight"], float)


class TestJudgeLLMValidator:
    """Tests for JudgeLLMValidator."""

    @pytest.mark.asyncio
    async def test_judge_llm_validation_success(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles,
        mock_llm_client
    ):
        """Test successful Judge LLM validation."""
        validator = JudgeLLMValidator(llm_client=mock_llm_client)

        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Check result structure
        assert result.success is True
        assert result.score is not None
        assert 0.0 <= result.score <= 1.0
        assert result.reasoning is not None

        # Check metadata
        assert "plausibility" in result.metadata
        assert "causality" in result.metadata
        assert "coherence" in result.metadata

        # LLM should have been called
        mock_llm_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_judge_llm_handles_json_with_markdown(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles
    ):
        """Test Judge LLM handles JSON wrapped in markdown code blocks."""
        # Create mock client that returns JSON in markdown
        mock_client = Mock()

        async def mock_completion(*args, **kwargs):
            return LLMResponse(
                id="test",
                content='```json\n{"plausibility": 4, "causality": 5, "coherence": 4, "reasoning": "Test"}\n```',
                role=LLMRole.ASSISTANT,
                tool_calls=None,
                finish_reason="stop",
                model="test",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            )

        mock_client.chat_completion = AsyncMock(side_effect=mock_completion)

        validator = JudgeLLMValidator(llm_client=mock_client)
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Should successfully parse despite markdown
        assert result.success is True
        assert result.metadata["plausibility"] == 4

    @pytest.mark.asyncio
    async def test_judge_llm_handles_invalid_json(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles
    ):
        """Test Judge LLM handles invalid JSON gracefully."""
        # Create mock client that returns invalid JSON
        mock_client = Mock()

        async def mock_completion(*args, **kwargs):
            return LLMResponse(
                id="test",
                content="This is not valid JSON",
                role=LLMRole.ASSISTANT,
                tool_calls=None,
                finish_reason="stop",
                model="test",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            )

        mock_client.chat_completion = AsyncMock(side_effect=mock_completion)

        validator = JudgeLLMValidator(llm_client=mock_client)
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Should fail gracefully
        assert result.success is False
        assert "JSON parsing failed" in result.error
        assert result.score == 0.5  # Neutral score

    @pytest.mark.asyncio
    async def test_judge_llm_score_calculation(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles
    ):
        """Test Judge LLM score normalization."""
        # Create mock client with known scores
        mock_client = Mock()

        async def mock_completion(*args, **kwargs):
            return LLMResponse(
                id="test",
                content='{"plausibility": 5, "causality": 5, "coherence": 5, "reasoning": "Perfect"}',
                role=LLMRole.ASSISTANT,
                tool_calls=None,
                finish_reason="stop",
                model="test",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            )

        mock_client.chat_completion = AsyncMock(side_effect=mock_completion)

        validator = JudgeLLMValidator(llm_client=mock_client)
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Perfect 5/5/5 should give score of 1.0
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_judge_llm_low_score_fails(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles
    ):
        """Test Judge LLM fails narratives with low scores."""
        # Create mock client with low scores
        mock_client = Mock()

        async def mock_completion(*args, **kwargs):
            return LLMResponse(
                id="test",
                content='{"plausibility": 1, "causality": 1, "coherence": 1, "reasoning": "Poor"}',
                role=LLMRole.ASSISTANT,
                tool_calls=None,
                finish_reason="stop",
                model="test",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            )

        mock_client.chat_completion = AsyncMock(side_effect=mock_completion)

        validator = JudgeLLMValidator(llm_client=mock_client)
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Low scores should fail
        assert result.passed is False
        assert result.score == 0.0  # 1/1/1 normalizes to 0.0

    @pytest.mark.asyncio
    async def test_judge_llm_handles_llm_error(
        self,
        sample_narrative,
        sample_anomaly,
        sample_news_articles
    ):
        """Test Judge LLM handles LLM errors gracefully."""
        # Create mock client that raises exception
        mock_client = Mock()
        mock_client.chat_completion = AsyncMock(side_effect=Exception("LLM API error"))

        validator = JudgeLLMValidator(llm_client=mock_client)
        result = await validator.validate(
            sample_narrative,
            sample_anomaly,
            sample_news_articles
        )

        # Should fail gracefully
        assert result.success is False
        assert "LLM validation failed" in result.error
        assert result.score == 0.5  # Neutral score on error
