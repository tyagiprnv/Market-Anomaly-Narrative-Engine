"""Pydantic models for agent tool inputs and outputs."""

from datetime import datetime
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base class for tool inputs."""

    pass


class ToolOutput(BaseModel):
    """Base class for tool outputs."""

    success: bool
    error: str | None = None


class VerifyTimestampInput(ToolInput):
    """Input for verify_timestamp tool.

    Attributes:
        news_timestamp: Timestamp when the news was published
        anomaly_timestamp: Timestamp when the anomaly was detected
        threshold_minutes: Time threshold in minutes (default: 30)
    """

    news_timestamp: datetime
    anomaly_timestamp: datetime
    threshold_minutes: int = 30


class VerifyTimestampOutput(ToolOutput):
    """Output for verify_timestamp tool.

    Attributes:
        success: Whether the tool executed successfully
        is_causal: Whether news could have caused the anomaly (published before)
        time_diff_minutes: Time difference in minutes (negative = news before anomaly)
        timing_tag: 'pre_event' or 'post_event'
        error: Error message if execution failed
    """

    is_causal: bool | None = None
    time_diff_minutes: float | None = None
    timing_tag: str | None = None


class SentimentCheckInput(ToolInput):
    """Input for sentiment_check tool.

    Attributes:
        texts: List of text snippets to analyze
    """

    texts: list[str]


class SentimentCheckOutput(ToolOutput):
    """Output for sentiment_check tool.

    Attributes:
        success: Whether the tool executed successfully
        sentiments: List of sentiment scores (-1 to 1) for each text
        average_sentiment: Average sentiment across all texts
        dominant_label: 'positive', 'negative', or 'neutral'
        error: Error message if execution failed
    """

    sentiments: list[float] | None = None
    average_sentiment: float | None = None
    dominant_label: str | None = None


class SearchHistoricalInput(ToolInput):
    """Input for search_historical tool.

    Attributes:
        symbol: Crypto symbol to search for
        anomaly_type: Type of anomaly (price_spike, price_drop, volume_spike)
        min_similarity: Minimum similarity threshold (0-1)
        limit: Maximum number of results to return
    """

    symbol: str
    anomaly_type: str
    min_similarity: float = 0.7
    limit: int = 5


class HistoricalAnomaly(BaseModel):
    """Single historical anomaly result."""

    id: str
    symbol: str
    detected_at: datetime
    anomaly_type: str
    price_change_pct: float
    narrative_text: str | None = None
    similarity_score: float


class SearchHistoricalOutput(ToolOutput):
    """Output for search_historical tool.

    Attributes:
        success: Whether the tool executed successfully
        results: List of similar historical anomalies
        count: Number of results found
        error: Error message if execution failed
    """

    results: list[HistoricalAnomaly] | None = None
    count: int = 0


class CheckMarketContextInput(ToolInput):
    """Input for check_market_context tool.

    Attributes:
        target_symbol: Symbol to check context for
        reference_symbols: Symbols to compare against (e.g., BTC-USD, ETH-USD)
        timestamp: Timestamp to check
        window_minutes: Time window around timestamp
    """

    target_symbol: str
    reference_symbols: list[str] = Field(default=["BTC-USD", "ETH-USD"])
    timestamp: datetime
    window_minutes: int = 10


class MarketContext(BaseModel):
    """Market context for a single symbol."""

    symbol: str
    price_change_pct: float | None = None
    is_moving: bool
    direction: str | None = None  # 'up', 'down', or None


class CheckMarketContextOutput(ToolOutput):
    """Output for check_market_context tool.

    Attributes:
        success: Whether the tool executed successfully
        target_context: Context for the target symbol
        reference_contexts: List of reference symbol contexts
        is_market_wide: Whether this appears to be a market-wide movement
        correlation_description: Human-readable correlation description
        error: Error message if execution failed
    """

    target_context: MarketContext | None = None
    reference_contexts: list[MarketContext] | None = None
    is_market_wide: bool = False
    correlation_description: str | None = None


class CheckSocialSentimentInput(ToolInput):
    """Input for check_social_sentiment tool.

    Attributes:
        symbol: Symbol to check sentiment for
        news_articles: List of news article titles/summaries to analyze
        source_filter: Optional filter by source (e.g., 'reddit', 'cryptopanic')
    """

    symbol: str
    news_articles: list[str]
    source_filter: str | None = None


class CheckSocialSentimentOutput(ToolOutput):
    """Output for check_social_sentiment tool.

    Attributes:
        success: Whether the tool executed successfully
        average_sentiment: Average sentiment score (-1 to 1)
        sentiment_label: 'bullish', 'bearish', or 'neutral'
        article_count: Number of articles analyzed
        sentiment_distribution: Count of positive/negative/neutral articles
        error: Error message if execution failed
    """

    average_sentiment: float | None = None
    sentiment_label: str | None = None
    article_count: int = 0
    sentiment_distribution: dict[str, int] | None = None
