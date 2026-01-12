"""Tool to analyze social sentiment from news articles."""

import logging
from typing import Any

from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.models import (
    CheckSocialSentimentInput,
    CheckSocialSentimentOutput,
)

logger = logging.getLogger(__name__)

# Lazy import for transformers (heavy dependency)
_sentiment_pipeline = None


def _get_sentiment_pipeline():
    """Lazy load FinBERT sentiment analysis pipeline."""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            from transformers import pipeline

            # Use FinBERT model for financial sentiment analysis
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
            )
            logger.info("Loaded FinBERT sentiment analysis model")
        except ImportError:
            logger.error("transformers library not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise

    return _sentiment_pipeline


class CheckSocialSentimentTool(AgentTool):
    """Analyzes social sentiment from news articles and social media.

    Aggregates sentiment across multiple news articles to understand
    overall market sentiment around a specific crypto asset. Particularly
    useful for analyzing Reddit discussions, CryptoPanic news, and other
    social media sources.

    Example:
        Articles: ["BTC rallies to new high", "Bitcoin adoption grows",
                   "Concerns over BTC volatility"]
        → average_sentiment: 0.45, label: "bullish", positive: 2, negative: 1
    """

    name = "check_social_sentiment"
    description = (
        "Analyze social sentiment from news articles and social media. "
        "Aggregates sentiment across multiple sources (Reddit, CryptoPanic, etc.) "
        "to understand overall market sentiment. Returns bullish/bearish/neutral "
        "label and sentiment distribution."
    )

    @classmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Crypto symbol to analyze sentiment for (e.g., 'BTC-USD')",
                },
                "news_articles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of news article titles/summaries to analyze",
                    "minItems": 1,
                },
                "source_filter": {
                    "type": "string",
                    "description": "Optional filter by source (e.g., 'reddit', 'cryptopanic')",
                },
            },
            "required": ["symbol", "news_articles"],
        }

    async def execute(self, **kwargs: Any) -> CheckSocialSentimentOutput:
        """Execute social sentiment analysis.

        Args:
            symbol: Crypto symbol to analyze
            news_articles: List of article titles/summaries
            source_filter: Optional source filter

        Returns:
            CheckSocialSentimentOutput with aggregated sentiment
        """
        try:
            symbol = kwargs.get("symbol")
            news_articles = kwargs.get("news_articles", [])
            source_filter = kwargs.get("source_filter")

            if not symbol or not news_articles:
                return self._create_error_output(
                    "symbol and news_articles are required", CheckSocialSentimentOutput
                )

            # Truncate long articles
            truncated_articles = [article[:500] for article in news_articles]

            # Load sentiment pipeline
            pipeline = _get_sentiment_pipeline()

            # Run sentiment analysis
            results = pipeline(truncated_articles)

            # Convert FinBERT labels to normalized scores
            sentiments = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0

            for result in results:
                label = result["label"].lower()
                score = result["score"]  # Confidence score 0-1

                # Convert to -1 to 1 scale and count
                if label == "positive":
                    normalized_score = score  # 0 to 1
                    positive_count += 1
                elif label == "negative":
                    normalized_score = -score  # -1 to 0
                    negative_count += 1
                else:  # neutral
                    normalized_score = 0.0
                    neutral_count += 1

                sentiments.append(normalized_score)

            # Calculate average sentiment
            average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            # Determine sentiment label (for crypto: bullish/bearish/neutral)
            if average_sentiment > 0.2:
                sentiment_label = "bullish"
            elif average_sentiment < -0.2:
                sentiment_label = "bearish"
            else:
                sentiment_label = "neutral"

            # Create sentiment distribution
            sentiment_distribution = {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count,
            }

            logger.info(
                f"Social sentiment for {symbol}: {sentiment_label} "
                f"(avg={average_sentiment:.2f}, n={len(news_articles)})"
            )

            return CheckSocialSentimentOutput(
                success=True,
                average_sentiment=average_sentiment,
                sentiment_label=sentiment_label,
                article_count=len(news_articles),
                sentiment_distribution=sentiment_distribution,
            )

        except ImportError:
            return self._create_error_output(
                "transformers library not installed. Install with: pip install transformers",
                CheckSocialSentimentOutput,
            )
        except Exception as e:
            logger.error(f"Error in check_social_sentiment: {e}")
            return self._create_error_output(str(e), CheckSocialSentimentOutput)
