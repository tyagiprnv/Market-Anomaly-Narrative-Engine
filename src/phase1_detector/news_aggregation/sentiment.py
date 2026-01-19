"""Keyword-based sentiment extraction for RSS and other news sources."""

import re
from typing import Pattern

# Bullish keywords indicating positive market sentiment
BULLISH_KEYWORDS: list[str] = [
    "surge",
    "rally",
    "breakout",
    "break",  # breaking through, breakthrough
    "soar",
    "moon",
    "pump",
    "bullish",
    "gain",  # gains, gaining
    "rise",  # rising, rises
    "spike",
    "jump",
    "skyrocket",
    "boom",
    "uptick",
    "positive",
    "growth",
    "strong",
    "outperform",
]

# Bearish keywords indicating negative market sentiment
BEARISH_KEYWORDS: list[str] = [
    "crash",
    "plummet",
    "dump",
    "collapse",
    "tank",
    "dip",
    "bearish",
    "losses",
    "fall",
    "drop",
    "decline",
    "plunge",
    "slump",
    "downturn",
    "negative",
    "weak",
    "underperform",
]


def _compile_patterns(keywords: list[str]) -> list[Pattern]:
    """Compile regex patterns for keywords with word boundaries.

    Matches keywords with common inflections (e.g., surge, surges, surging).
    Handles dropping of final 'e' before 'ing' (e.g., collapse -> collapsing).

    Args:
        keywords: List of keywords to match

    Returns:
        List of compiled regex patterns
    """
    patterns = []
    for keyword in keywords:
        # Handle words ending in 'e' that drop it before 'ing'
        if keyword.endswith('e'):
            stem = keyword[:-1]
            # Match: word, words, wordes, word+ing, word+ed (with or without 'e')
            pattern = rf"\b{re.escape(stem)}e?(?:s|ing|ed|es)?\b"
        else:
            # Match: word, words, wording, worded, wordes
            pattern = rf"\b{re.escape(keyword)}(?:s|ing|ed|es)?\b"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    return patterns


# Pre-compile patterns for performance
_BULLISH_PATTERNS = _compile_patterns(BULLISH_KEYWORDS)
_BEARISH_PATTERNS = _compile_patterns(BEARISH_KEYWORDS)


def extract_sentiment(title: str, summary: str | None = None) -> float:
    """Extract sentiment score from article title and summary using keyword matching.

    Sentiment is calculated as:
        (bullish_count - bearish_count) / max(total_count, 1)

    The result is clamped to [-1.0, 1.0] range where:
        -1.0 = Strongly bearish
         0.0 = Neutral
         1.0 = Strongly bullish

    Args:
        title: Article title (required)
        summary: Article summary or content (optional)

    Returns:
        Sentiment score in range [-1.0, 1.0]

    Examples:
        >>> extract_sentiment("Bitcoin surges to new all-time high")
        1.0
        >>> extract_sentiment("Market crashes as Bitcoin plummets")
        -1.0
        >>> extract_sentiment("Bitcoin price analysis for today")
        0.0
    """
    # Combine title and summary for analysis
    text = title.lower()
    if summary:
        text += " " + summary.lower()

    # Count keyword matches
    bullish_count = sum(1 for pattern in _BULLISH_PATTERNS if pattern.search(text))
    bearish_count = sum(1 for pattern in _BEARISH_PATTERNS if pattern.search(text))

    total_count = bullish_count + bearish_count

    # Return neutral if no sentiment keywords found
    if total_count == 0:
        return 0.0

    # Calculate normalized sentiment score
    sentiment = (bullish_count - bearish_count) / total_count

    # Clamp to valid range [-1.0, 1.0]
    return max(-1.0, min(1.0, sentiment))


def classify_sentiment(sentiment_score: float) -> str:
    """Classify sentiment score into human-readable categories.

    Args:
        sentiment_score: Sentiment score in range [-1.0, 1.0]

    Returns:
        Sentiment classification: "strongly_bullish", "bullish", "neutral",
        "bearish", or "strongly_bearish"
    """
    if sentiment_score >= 0.6:
        return "strongly_bullish"
    elif sentiment_score >= 0.2:
        return "bullish"
    elif sentiment_score <= -0.6:
        return "strongly_bearish"
    elif sentiment_score <= -0.2:
        return "bearish"
    else:
        return "neutral"
