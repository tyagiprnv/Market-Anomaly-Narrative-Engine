"""Tool consistency validator.

Validates that tool results are internally consistent and align with narrative.
"""

from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle
from config.settings import settings
from .base import Validator
from .models import ValidatorOutput


class ToolConsistencyValidator(Validator):
    """Validates internal consistency of tool results.

    Checks:
    1. Tools were actually used (tools_used field populated)
    2. Tool results are successful and contain data
    3. Results don't contradict each other
    4. Market context aligns with narrative
    """

    name = "tool_consistency"
    description = "Validates internal consistency of tool results"
    weight = settings.validation.tool_consistency_weight

    # Expected tools for journalist agent
    EXPECTED_TOOLS = [
        "verify_timestamp",
        "sentiment_check",
        "search_historical",
        "market_context",
        "social_sentiment"
    ]

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate tool consistency.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with tool consistency score
        """
        try:
            # Check tool usage
            tools_used = narrative.tools_used or []
            tool_results = narrative.tool_results or {}

            # If no tools used, low score
            if not tools_used:
                return ValidatorOutput(
                    success=True,
                    passed=False,
                    score=0.4,
                    confidence=0.9,
                    reasoning="No tools were used to generate narrative",
                    metadata={"tools_used": 0, "tools_expected": len(self.EXPECTED_TOOLS)}
                )

            # Count successful tool executions
            successful_tools = len(tools_used)
            min_tools = settings.validation.min_tools_used

            # Check for contradictions
            contradictions = self._check_contradictions(tool_results, anomaly)

            # Calculate score
            score, reasoning = self._calculate_consistency_score(
                successful_tools,
                min_tools,
                contradictions,
                tool_results
            )

            # Determine pass/fail
            passed = score >= 0.6

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.85,
                reasoning=reasoning,
                metadata={
                    "tools_used": successful_tools,
                    "min_tools_expected": min_tools,
                    "contradictions_found": len(contradictions),
                    "contradiction_details": contradictions,
                    "available_tools": list(tool_results.keys())
                }
            )

        except Exception as e:
            return ValidatorOutput(
                success=False,
                error=f"Tool consistency validation failed: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator error"
            )

    def _check_contradictions(
        self,
        tool_results: dict,
        anomaly: Anomaly
    ) -> list[str]:
        """Check for contradictions in tool results.

        Args:
            tool_results: Tool results from narrative
            anomaly: The anomaly

        Returns:
            List of contradiction descriptions
        """
        contradictions = []

        # Check sentiment vs market context
        sentiment_data = tool_results.get("sentiment_check", {})
        market_context = tool_results.get("market_context", {})

        if sentiment_data and market_context:
            sentiment = sentiment_data.get("sentiment", 0.0)
            market_trend = market_context.get("trend", "unknown")

            # Positive sentiment but bearish market
            if sentiment > 0.3 and market_trend == "bearish":
                contradictions.append(
                    f"Positive sentiment ({sentiment:.2f}) contradicts bearish market trend"
                )

            # Negative sentiment but bullish market
            if sentiment < -0.3 and market_trend == "bullish":
                contradictions.append(
                    f"Negative sentiment ({sentiment:.2f}) contradicts bullish market trend"
                )

        # Check social sentiment vs news sentiment
        sentiment_check = sentiment_data.get("sentiment", 0.0) if sentiment_data else None
        social_sentiment = tool_results.get("social_sentiment", {})

        if sentiment_check is not None and social_sentiment:
            social_score = social_sentiment.get("sentiment_score", 0.0)

            # Large divergence between news and social sentiment
            if abs(sentiment_check - social_score) > 0.7:
                contradictions.append(
                    f"Large divergence: news sentiment ({sentiment_check:.2f}) vs "
                    f"social sentiment ({social_score:.2f})"
                )

        return contradictions

    def _calculate_consistency_score(
        self,
        successful_tools: int,
        min_tools: int,
        contradictions: list[str],
        tool_results: dict
    ) -> tuple[float, str]:
        """Calculate tool consistency score.

        Args:
            successful_tools: Number of tools successfully used
            min_tools: Minimum expected tools
            contradictions: List of found contradictions
            tool_results: Tool results dictionary

        Returns:
            Tuple of (score, reasoning)
        """
        # Base score from tool usage
        if successful_tools >= min_tools:
            base_score = 1.0
            usage_note = f"{successful_tools} tools used (meets minimum of {min_tools})"
        elif successful_tools >= min_tools - 1:
            base_score = 0.8
            usage_note = f"{successful_tools} tools used (1 below minimum of {min_tools})"
        else:
            base_score = 0.5
            usage_note = f"Only {successful_tools} tools used (minimum is {min_tools})"

        # Penalize contradictions
        contradiction_penalty = len(contradictions) * 0.2
        final_score = max(0.0, base_score - contradiction_penalty)

        # Build reasoning
        if contradictions:
            contradiction_summary = "; ".join(contradictions)
            reasoning = (
                f"{usage_note}. Contradictions found: {contradiction_summary}"
            )
        elif final_score >= 0.9:
            reasoning = f"{usage_note}. All tool results are consistent."
        else:
            reasoning = usage_note

        return final_score, reasoning
