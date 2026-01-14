"""Judge LLM validator using LLM-based assessment."""

import json
import logging
from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle
from src.llm.client import LLMClient
from src.llm.models import LLMMessage, LLMRole
from config.settings import settings
from ..prompts import JUDGE_SYSTEM_PROMPT, format_validation_context
from .base import Validator
from .models import ValidatorOutput

logger = logging.getLogger(__name__)


class JudgeLLMValidator(Validator):
    """LLM-based validation for narrative plausibility and coherence.

    This validator uses a judge LLM to assess:
    1. Plausibility: Could this explain the price movement?
    2. Causality: Does timing support causation?
    3. Coherence: Is the narrative internally consistent?

    Only called if rule validators pass minimum threshold (conditional execution).
    """

    name = "judge_llm"
    description = "LLM-based validation for plausibility, causality, and coherence"
    weight = settings.validation.judge_llm_weight

    def __init__(self, llm_client: LLMClient | None = None):
        """Initialize Judge LLM validator.

        Args:
            llm_client: LLM client instance. If None, creates new client.
        """
        self.llm_client = llm_client or LLMClient(
            model=settings.validation.judge_llm_model,
            temperature=settings.validation.judge_llm_temperature,
        )

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate narrative using Judge LLM.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with LLM assessment
        """
        try:
            # Format context for LLM
            context = format_validation_context(narrative, anomaly, news_articles)

            # Create messages
            messages = [
                LLMMessage(
                    role=LLMRole.SYSTEM,
                    content=JUDGE_SYSTEM_PROMPT
                ),
                LLMMessage(
                    role=LLMRole.USER,
                    content=context
                )
            ]

            # Call LLM
            logger.debug(f"Calling Judge LLM for narrative {narrative.id}")
            response = await self.llm_client.chat_completion(messages)

            # Parse JSON response
            assessment = self._parse_llm_response(response.content)

            # Calculate score
            score = self._calculate_score(assessment)

            # Determine pass/fail
            passed = score >= (settings.validation.judge_llm_min_score / 5.0)

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.8,  # LLM assessments have inherent uncertainty
                reasoning=assessment.get("reasoning", "No reasoning provided"),
                metadata={
                    "plausibility": assessment.get("plausibility"),
                    "causality": assessment.get("causality"),
                    "coherence": assessment.get("coherence"),
                    "raw_response": response.content,
                    "model": response.model,
                    "tokens_used": response.usage.total_tokens
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Judge LLM JSON response: {e}")
            return ValidatorOutput(
                success=False,
                error=f"JSON parsing failed: {str(e)}",
                score=0.5,  # Neutral score on parse failure
                confidence=0.0,
                reasoning="LLM response was not valid JSON"
            )

        except Exception as e:
            logger.error(f"Judge LLM validation failed: {e}", exc_info=True)
            return ValidatorOutput(
                success=False,
                error=f"LLM validation failed: {str(e)}",
                score=0.5,  # Neutral score on error
                confidence=0.0,
                reasoning="LLM validation unavailable"
            )

    def _parse_llm_response(self, content: str | None) -> dict[str, Any]:
        """Parse JSON response from LLM.

        Args:
            content: LLM response content

        Returns:
            Parsed assessment dictionary

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        if not content:
            raise json.JSONDecodeError("Empty response", "", 0)

        # Try to extract JSON from markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            # Remove markdown code fence
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        # Parse JSON
        assessment = json.loads(content)

        # Validate required fields
        required_fields = ["plausibility", "causality", "coherence", "reasoning"]
        for field in required_fields:
            if field not in assessment:
                raise ValueError(f"Missing required field: {field}")

        # Validate score ranges (1-5)
        for field in ["plausibility", "causality", "coherence"]:
            score = assessment[field]
            if not isinstance(score, (int, float)) or not (1 <= score <= 5):
                raise ValueError(f"{field} must be between 1 and 5, got {score}")

        return assessment

    def _calculate_score(self, assessment: dict[str, Any]) -> float:
        """Calculate normalized score from assessment.

        Args:
            assessment: Parsed LLM assessment

        Returns:
            Normalized score (0-1)
        """
        # Average the three scores and normalize to 0-1
        plausibility = assessment["plausibility"]
        causality = assessment["causality"]
        coherence = assessment["coherence"]

        # Simple average (could be weighted)
        average_score = (plausibility + causality + coherence) / 3

        # Normalize from 1-5 scale to 0-1 scale
        normalized = (average_score - 1) / 4

        return max(0.0, min(1.0, normalized))
