"""Sentiment match validator.

Validates that narrative sentiment aligns with news sentiment and price direction.
"""

from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle, AnomalyTypeEnum
from config.settings import settings
from .base import Validator
from .models import ValidatorOutput


class SentimentMatchValidator(Validator):
    """Validates sentiment alignment between narrative, news, and price movement.

    Checks:
    1. Sentiment from tool_results["sentiment_check"] aligns with price direction
    2. Positive news + price spike = PASS
    3. Negative news + price drop = PASS
    4. Contradictory sentiments = FAIL
    """

    name = "sentiment_match"
    description = "Validates sentiment alignment between narrative, news, and price movement"
    weight = settings.validation.sentiment_match_weight

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate sentiment alignment.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with sentiment alignment score
        """
        try:
            # Extract sentiment from tool results
            tool_results = narrative.tool_results or {}
            sentiment_data = tool_results.get("sentiment_check", {})

            # If no sentiment data, return neutral score
            if not sentiment_data or "sentiment" not in sentiment_data:
                return ValidatorOutput(
                    success=True,
                    passed=None,
                    score=0.5,
                    confidence=0.3,
                    reasoning="No sentiment data available from tools",
                    metadata={"has_sentiment_data": False}
                )

            sentiment_value = sentiment_data.get("sentiment", 0.0)

            # Determine expected sentiment based on anomaly type
            expected_positive = anomaly.anomaly_type in [
                AnomalyTypeEnum.PRICE_SPIKE,
                AnomalyTypeEnum.VOLUME_SPIKE
            ]
            expected_negative = anomaly.anomaly_type == AnomalyTypeEnum.PRICE_DROP

            # Check if sentiment is in neutral range
            neutral_lower = settings.validation.sentiment_neutral_range_lower
            neutral_upper = settings.validation.sentiment_neutral_range_upper
            is_neutral = neutral_lower <= sentiment_value <= neutral_upper

            # Calculate score based on alignment
            score, reasoning = self._calculate_sentiment_score(
                sentiment_value,
                expected_positive,
                expected_negative,
                is_neutral
            )

            # Determine pass/fail
            passed = score >= settings.validation.sentiment_alignment_threshold

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.9,
                reasoning=reasoning,
                metadata={
                    "sentiment_value": sentiment_value,
                    "anomaly_type": anomaly.anomaly_type.value,
                    "expected_positive": expected_positive,
                    "expected_negative": expected_negative,
                    "is_neutral": is_neutral
                }
            )

        except Exception as e:
            return ValidatorOutput(
                success=False,
                error=f"Sentiment match validation failed: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator error"
            )

    def _calculate_sentiment_score(
        self,
        sentiment_value: float,
        expected_positive: bool,
        expected_negative: bool,
        is_neutral: bool
    ) -> tuple[float, str]:
        """Calculate sentiment alignment score.

        Args:
            sentiment_value: Sentiment score from tools (-1 to 1)
            expected_positive: Whether positive sentiment is expected
            expected_negative: Whether negative sentiment is expected
            is_neutral: Whether sentiment is neutral

        Returns:
            Tuple of (score, reasoning)
        """
        # Perfect alignment
        if expected_positive and sentiment_value > 0.2:
            return 1.0, f"Positive sentiment ({sentiment_value:.2f}) aligns with price spike"

        if expected_negative and sentiment_value < -0.2:
            return 1.0, f"Negative sentiment ({sentiment_value:.2f}) aligns with price drop"

        # Neutral sentiment is acceptable
        if is_neutral:
            return 0.5, f"Neutral sentiment ({sentiment_value:.2f}) - neither confirms nor contradicts"

        # Contradictory sentiment
        if expected_positive and sentiment_value < -0.2:
            return 0.0, f"Negative sentiment ({sentiment_value:.2f}) contradicts price spike"

        if expected_negative and sentiment_value > 0.2:
            return 0.0, f"Positive sentiment ({sentiment_value:.2f}) contradicts price drop"

        # Volume spike with any sentiment
        if not expected_positive and not expected_negative:
            return 0.7, f"Volume spike with sentiment {sentiment_value:.2f} - partial alignment"

        # Default case
        return 0.5, f"Ambiguous sentiment alignment (sentiment: {sentiment_value:.2f})"
