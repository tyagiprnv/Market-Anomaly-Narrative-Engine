"""Tool for financial sentiment analysis using FinBERT."""

import logging
from typing import Any

from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.models import SentimentCheckInput, SentimentCheckOutput

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
            logger.error("transformers library not installed. Install with: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise

    return _sentiment_pipeline


class SentimentCheckTool(AgentTool):
    """Analyzes sentiment of financial text using FinBERT.

    Uses the FinBERT model (ProsusAI/finbert) fine-tuned on financial text
    to classify sentiment as positive, negative, or neutral. Returns
    normalized scores (-1 to 1) where -1 is most bearish and 1 is most bullish.

    Example:
        Text: "Bitcoin crashes 10% amid regulatory fears"
        → sentiment: -0.85, label: "negative"

        Text: "Ethereum ETF approval boosts crypto market"
        → sentiment: 0.92, label: "positive"
    """

    name = "sentiment_check"
    description = (
        "Analyze sentiment of financial text using FinBERT model. "
        "Returns sentiment scores (-1 to 1) for each text, average sentiment, "
        "and dominant label (positive/negative/neutral). Use this to understand "
        "market sentiment in news articles and social media."
    )

    @classmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of text snippets to analyze (e.g., headlines, summaries)",
                    "minItems": 1,
                },
            },
            "required": ["texts"],
        }

    def __init__(self):
        """Initialize the sentiment checker."""
        # Pipeline will be loaded on first use
        pass

    async def execute(self, **kwargs: Any) -> SentimentCheckOutput:
        """Execute sentiment analysis.

        Args:
            texts: List of text snippets to analyze

        Returns:
            SentimentCheckOutput with sentiment scores and labels
        """
        try:
            texts = kwargs.get("texts", [])

            if not texts:
                return self._create_error_output(
                    "At least one text is required for sentiment analysis",
                    SentimentCheckOutput,
                )

            # Truncate very long texts to avoid model limits (512 tokens)
            truncated_texts = [text[:500] for text in texts]

            # Load sentiment pipeline
            pipeline = _get_sentiment_pipeline()

            # Run sentiment analysis
            results = pipeline(truncated_texts)

            # Convert FinBERT labels to normalized scores
            # FinBERT outputs: 'positive', 'negative', 'neutral'
            sentiments = []
            for result in results:
                label = result["label"].lower()
                score = result["score"]  # Confidence score 0-1

                # Convert to -1 to 1 scale
                if label == "positive":
                    normalized_score = score  # 0 to 1
                elif label == "negative":
                    normalized_score = -score  # -1 to 0
                else:  # neutral
                    normalized_score = 0.0

                sentiments.append(normalized_score)

            # Calculate average sentiment
            average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            # Determine dominant label
            if average_sentiment > 0.2:
                dominant_label = "positive"
            elif average_sentiment < -0.2:
                dominant_label = "negative"
            else:
                dominant_label = "neutral"

            logger.info(
                f"Sentiment analysis: {len(texts)} texts, "
                f"avg={average_sentiment:.2f}, label={dominant_label}"
            )

            return SentimentCheckOutput(
                success=True,
                sentiments=sentiments,
                average_sentiment=average_sentiment,
                dominant_label=dominant_label,
            )

        except ImportError:
            return self._create_error_output(
                "transformers library not installed. Install with: pip install transformers",
                SentimentCheckOutput,
            )
        except Exception as e:
            logger.error(f"Error in sentiment_check: {e}")
            return self._create_error_output(str(e), SentimentCheckOutput)
