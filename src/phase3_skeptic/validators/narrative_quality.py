"""Narrative quality validator.

Validates basic text quality and formatting requirements.
"""

import re
from typing import Any

from src.database.models import Narrative, Anomaly, NewsArticle
from config.settings import settings
from .base import Validator
from .models import ValidatorOutput


class NarrativeQualityValidator(Validator):
    """Validates basic narrative text quality.

    Checks:
    1. Exactly 2 sentences (as per requirements)
    2. No hedging language ("possibly", "might have")
    3. No markdown formatting or bullets
    4. Not the "Unknown" fallback response
    5. Appropriate length (not too short or too long)
    """

    name = "narrative_quality"
    description = "Validates basic narrative text quality and formatting"
    weight = settings.validation.narrative_quality_weight

    # Sentence boundaries (basic regex)
    SENTENCE_PATTERN = r'[.!?]+(?:\s+|$)'

    # Format issues to detect
    MARKDOWN_PATTERNS = [
        r'\*\*',  # Bold
        r'__',    # Bold/italic
        r'\*',    # Italic/bullets (check context)
        r'#',     # Headers
        r'\[.*\]\(.*\)',  # Links
        r'```',   # Code blocks
        r'-\s',   # List items (with space after)
    ]

    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate narrative quality.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context

        Returns:
            ValidatorOutput with narrative quality score
        """
        try:
            narrative_text = narrative.narrative_text

            # Check for "Unknown" fallback
            if "Unknown" in narrative_text or "unknown" in narrative_text.lower():
                return ValidatorOutput(
                    success=True,
                    passed=False,
                    score=0.5,
                    confidence=1.0,
                    reasoning="Narrative contains 'Unknown' - indicates low confidence explanation",
                    metadata={"is_unknown_fallback": True}
                )

            # Count sentences
            sentence_count = self._count_sentences(narrative_text)
            max_sentences = settings.validation.max_sentence_count

            # Check for hedging language
            hedging_found = self._check_hedging(narrative_text)

            # Check for markdown formatting
            format_issues = self._check_formatting(narrative_text)

            # Check length
            length_ok = 50 <= len(narrative_text) <= 500

            # Calculate score
            score, reasoning = self._calculate_quality_score(
                sentence_count,
                max_sentences,
                hedging_found,
                format_issues,
                length_ok,
                len(narrative_text)
            )

            # Determine pass/fail
            passed = score >= 0.6

            return ValidatorOutput(
                success=True,
                passed=passed,
                score=score,
                confidence=0.95,
                reasoning=reasoning,
                metadata={
                    "sentence_count": sentence_count,
                    "max_sentences": max_sentences,
                    "hedging_keywords_found": hedging_found,
                    "format_issues": format_issues,
                    "text_length": len(narrative_text),
                    "length_ok": length_ok
                }
            )

        except Exception as e:
            return ValidatorOutput(
                success=False,
                error=f"Narrative quality validation failed: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator error"
            )

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text.

        Args:
            text: Narrative text

        Returns:
            Number of sentences
        """
        # Split by sentence boundaries
        sentences = re.split(self.SENTENCE_PATTERN, text)
        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)

    def _check_hedging(self, text: str) -> list[str]:
        """Check for hedging language.

        Args:
            text: Narrative text

        Returns:
            List of hedging keywords found
        """
        text_lower = text.lower()
        hedging_keywords = settings.validation.hedging_keywords
        found = [
            keyword for keyword in hedging_keywords
            if keyword in text_lower
        ]
        return found

    def _check_formatting(self, text: str) -> list[str]:
        """Check for markdown formatting issues.

        Args:
            text: Narrative text

        Returns:
            List of format issues found
        """
        issues = []
        for pattern in self.MARKDOWN_PATTERNS:
            if re.search(pattern, text):
                issues.append(f"Found markdown pattern: {pattern}")

        return issues

    def _calculate_quality_score(
        self,
        sentence_count: int,
        max_sentences: int,
        hedging_found: list[str],
        format_issues: list[str],
        length_ok: bool,
        text_length: int
    ) -> tuple[float, str]:
        """Calculate narrative quality score.

        Args:
            sentence_count: Number of sentences
            max_sentences: Maximum allowed sentences
            hedging_found: List of hedging keywords found
            format_issues: List of format issues
            length_ok: Whether length is within range
            text_length: Character count

        Returns:
            Tuple of (score, reasoning)
        """
        issues = []
        score = 1.0

        # Check sentence count (strict requirement)
        if sentence_count != max_sentences:
            score -= 0.3
            issues.append(
                f"{sentence_count} sentences (expected exactly {max_sentences})"
            )

        # Check hedging (moderate penalty)
        if hedging_found:
            score -= 0.2
            hedging_str = ", ".join(hedging_found)
            issues.append(f"hedging language: {hedging_str}")

        # Check formatting (moderate penalty)
        if format_issues:
            score -= 0.2
            issues.append(f"{len(format_issues)} formatting issues")

        # Check length (minor penalty)
        if not length_ok:
            score -= 0.1
            issues.append(f"length {text_length} chars (expected 50-500)")

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        # Build reasoning
        if score == 1.0:
            reasoning = "Perfect narrative quality: 2 sentences, no hedging, clean formatting"
        elif score >= 0.7:
            issues_str = "; ".join(issues)
            reasoning = f"Good quality with minor issues: {issues_str}"
        elif score >= 0.5:
            issues_str = "; ".join(issues)
            reasoning = f"Acceptable quality with issues: {issues_str}"
        else:
            issues_str = "; ".join(issues)
            reasoning = f"Poor quality: {issues_str}"

        return score, reasoning
