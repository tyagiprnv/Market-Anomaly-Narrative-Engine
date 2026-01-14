"""Magnitude coherence validator.

Validates that narrative language matches the magnitude of the anomaly.
"""

import re
from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle
from config.settings import settings
from .base import Validator
from .models import ValidatorOutput


class MagnitudeCoherenceValidator(Validator):
    """Validates that narrative language matches anomaly magnitude.

    Checks:
    1. Large z-scores should have strong language ("crashed", "surged")
    2. Small z-scores should have moderate language ("rose", "fell")
    3. Flags exaggerated or understated descriptions
    """

    name = "magnitude_coherence"
    description = "Validates that narrative language matches anomaly magnitude"
    weight = settings.validation.magnitude_coherence_weight

    # Magnitude keywords by intensity
    STRONG_KEYWORDS = [
        "crashed", "plummeted", "collapsed", "surged", "soared", "skyrocketed",
        "massive", "dramatic", "sharp", "plunged", "spiked", "exploded"
    ]

    MODERATE_KEYWORDS = [
        "rose", "fell", "increased", "decreased", "dropped", "climbed",
        "gained", "lost", "moved", "shifted", "notable", "significant"
    ]

    WEAK_KEYWORDS = [
        "slight", "minor", "small", "marginal", "modest", "barely",
        "slightly", "minimal", "tiny", "little"
    ]

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate magnitude coherence.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with magnitude coherence score
        """
        try:
            # Get magnitude metrics
            z_score = abs(anomaly.z_score) if anomaly.z_score else 0.0
            price_change_pct = abs(anomaly.price_change_pct) if anomaly.price_change_pct else 0.0

            # Classify magnitude
            magnitude_tier = self._classify_magnitude(z_score, price_change_pct)

            # Analyze narrative language
            narrative_text = narrative.narrative_text.lower()
            language_intensity = self._analyze_language_intensity(narrative_text)

            # Calculate score based on alignment
            score, reasoning = self._calculate_magnitude_score(
                magnitude_tier,
                language_intensity,
                z_score,
                price_change_pct
            )

            # Determine pass/fail
            passed = score >= 0.5  # Moderate threshold for magnitude

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.85,
                reasoning=reasoning,
                metadata={
                    "z_score": z_score,
                    "price_change_pct": price_change_pct,
                    "magnitude_tier": magnitude_tier,
                    "language_intensity": language_intensity,
                }
            )

        except Exception as e:
            return ValidatorOutput(
                success=False,
                error=f"Magnitude coherence validation failed: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator error"
            )

    def _classify_magnitude(self, z_score: float, price_change_pct: float) -> str:
        """Classify anomaly magnitude into tiers.

        Args:
            z_score: Absolute z-score
            price_change_pct: Absolute price change percentage

        Returns:
            Magnitude tier: "large", "medium", or "small"
        """
        z_large = settings.validation.z_score_large
        z_small = settings.validation.z_score_small

        if z_score >= z_large or price_change_pct >= 10.0:
            return "large"
        elif z_score >= z_small or price_change_pct >= 5.0:
            return "medium"
        else:
            return "small"

    def _analyze_language_intensity(self, narrative_text: str) -> str:
        """Analyze language intensity in narrative.

        Args:
            narrative_text: Lowercase narrative text

        Returns:
            Language intensity: "strong", "moderate", "weak", or "neutral"
        """
        # Count keyword occurrences
        strong_count = sum(
            1 for keyword in self.STRONG_KEYWORDS
            if keyword in narrative_text
        )
        moderate_count = sum(
            1 for keyword in self.MODERATE_KEYWORDS
            if keyword in narrative_text
        )
        weak_count = sum(
            1 for keyword in self.WEAK_KEYWORDS
            if keyword in narrative_text
        )

        # Classify based on counts
        if strong_count > 0:
            return "strong"
        elif weak_count > 0:
            return "weak"
        elif moderate_count > 0:
            return "moderate"
        else:
            return "neutral"

    def _calculate_magnitude_score(
        self,
        magnitude_tier: str,
        language_intensity: str,
        z_score: float,
        price_change_pct: float
    ) -> tuple[float, str]:
        """Calculate magnitude coherence score.

        Args:
            magnitude_tier: Anomaly magnitude tier
            language_intensity: Narrative language intensity
            z_score: Absolute z-score
            price_change_pct: Absolute price change percentage

        Returns:
            Tuple of (score, reasoning)
        """
        # Perfect matches
        if magnitude_tier == "large" and language_intensity == "strong":
            return 1.0, (
                f"Strong language matches large magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        if magnitude_tier == "medium" and language_intensity == "moderate":
            return 1.0, (
                f"Moderate language matches medium magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        if magnitude_tier == "small" and language_intensity in ["weak", "moderate"]:
            return 1.0, (
                f"Appropriate language for small magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        # Neutral language is acceptable for any magnitude
        if language_intensity == "neutral":
            return 0.7, (
                f"Neutral language (no strong descriptors) for {magnitude_tier} magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        # Exaggerated language for small magnitude
        if magnitude_tier == "small" and language_intensity == "strong":
            return 0.3, (
                f"Exaggerated: strong language for small magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        # Understated language for large magnitude
        if magnitude_tier == "large" and language_intensity == "weak":
            return 0.4, (
                f"Understated: weak language for large magnitude "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        # Partial matches
        if magnitude_tier == "large" and language_intensity == "moderate":
            return 0.7, (
                f"Moderate language for large magnitude - acceptable but understated "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        if magnitude_tier == "medium" and language_intensity == "strong":
            return 0.7, (
                f"Strong language for medium magnitude - slightly exaggerated "
                f"(z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
            )

        # Default case
        return 0.6, (
            f"Language-magnitude alignment unclear: {language_intensity} language, "
            f"{magnitude_tier} magnitude (z-score: {z_score:.1f}, change: {price_change_pct:.1f}%)"
        )
