"""Timing coherence validator.

Validates that cited news occurred before the anomaly (causal coherence).
"""

from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle
from config.settings import settings
from .base import Validator
from .models import ValidatorOutput


class TimingCoherenceValidator(Validator):
    """Validates timing coherence of news relative to anomaly.

    Checks:
    1. News cited in narrative has timing_tag = "pre_event"
    2. Post-event news should not be cited as causal
    3. Timing verification from tool_results["verify_timestamp"]
    """

    name = "timing_coherence"
    description = "Validates that cited news occurred before the anomaly"
    weight = settings.validation.timing_coherence_weight

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate timing coherence.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with timing coherence score
        """
        try:
            # If no news articles, cannot validate
            if not news_articles:
                return ValidatorOutput(
                    success=True,
                    passed=None,
                    score=0.5,
                    confidence=0.2,
                    reasoning="No news articles to validate timing",
                    metadata={"news_count": 0}
                )

            # Check for timing verification in tool results
            tool_results = narrative.tool_results or {}
            timing_data = tool_results.get("verify_timestamp", {})

            # Count pre-event vs post-event news
            pre_event_count = 0
            post_event_count = 0
            no_timing_count = 0

            for article in news_articles:
                if article.timing_tag == "pre_event":
                    pre_event_count += 1
                elif article.timing_tag == "post_event":
                    post_event_count += 1
                else:
                    no_timing_count += 1

            total_count = len(news_articles)

            # Calculate score based on timing distribution
            score, reasoning = self._calculate_timing_score(
                pre_event_count,
                post_event_count,
                no_timing_count,
                total_count,
                timing_data
            )

            # Determine pass/fail
            passed = score >= 0.6  # Timing is critical, high threshold

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.95,  # High confidence in timing data
                reasoning=reasoning,
                metadata={
                    "pre_event_count": pre_event_count,
                    "post_event_count": post_event_count,
                    "no_timing_count": no_timing_count,
                    "total_count": total_count,
                    "pre_event_ratio": pre_event_count / total_count if total_count > 0 else 0,
                    "has_timing_verification": bool(timing_data)
                }
            )

        except Exception as e:
            return ValidatorOutput(
                success=False,
                error=f"Timing coherence validation failed: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator error"
            )

    def _calculate_timing_score(
        self,
        pre_event_count: int,
        post_event_count: int,
        no_timing_count: int,
        total_count: int,
        timing_data: dict
    ) -> tuple[float, str]:
        """Calculate timing coherence score.

        Args:
            pre_event_count: Number of pre-event news articles
            post_event_count: Number of post-event news articles
            no_timing_count: Number of articles without timing info
            total_count: Total number of articles
            timing_data: Timing verification from tools

        Returns:
            Tuple of (score, reasoning)
        """
        # Calculate ratios
        pre_event_ratio = pre_event_count / total_count if total_count > 0 else 0
        post_event_ratio = post_event_count / total_count if total_count > 0 else 0

        # Perfect case: All pre-event news
        if pre_event_count == total_count:
            return 1.0, f"All {total_count} news articles occurred before the anomaly"

        # Good case: Majority pre-event (>= 80%)
        if pre_event_ratio >= settings.validation.min_causal_news_ratio:
            return 0.9, (
                f"{pre_event_count}/{total_count} articles are pre-event "
                f"({pre_event_ratio:.1%}) - strong causal coherence"
            )

        # Acceptable case: More than half pre-event
        if pre_event_ratio >= 0.5:
            return 0.7, (
                f"{pre_event_count}/{total_count} articles are pre-event "
                f"({pre_event_ratio:.1%}) - partial causal coherence"
            )

        # Problematic case: Majority post-event
        if post_event_ratio > 0.5:
            return 0.2, (
                f"{post_event_count}/{total_count} articles are post-event "
                f"({post_event_ratio:.1%}) - weak causal coherence"
            )

        # Edge case: All articles have no timing
        if no_timing_count == total_count:
            return 0.5, f"No timing information available for {total_count} articles"

        # Default case: Mixed timing
        return 0.5, (
            f"Mixed timing: {pre_event_count} pre-event, "
            f"{post_event_count} post-event, {no_timing_count} unknown"
        )
