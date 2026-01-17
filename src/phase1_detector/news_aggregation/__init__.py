"""News aggregation module for Phase 1: Detector.

This module provides clients for fetching cryptocurrency news from multiple sources:
- CryptoPanic: Crypto-specific news aggregator with sentiment
- Reddit: Crypto subreddit discussions
- NewsAPI: General news from major outlets
- Grok: X/Twitter real-time data via xAI API (optional)

The NewsAggregator class combines all sources and provides time-windowed
news fetching for anomaly correlation.

Example:
    ```python
    from src.phase1_detector.news_aggregation import NewsAggregator
    from datetime import datetime

    # Initialize aggregator (uses settings from config)
    aggregator = NewsAggregator()

    # Get news around an anomaly
    anomaly_time = datetime.now()
    articles = await aggregator.get_news_for_anomaly(
        symbols=["BTC-USD"],
        anomaly_time=anomaly_time,
        window_minutes=30,
    )

    for article in articles:
        print(f"{article.source}: {article.title}")
    ```
"""

from src.phase1_detector.news_aggregation.models import (
    NewsArticle,
    RedditPost,
    CryptoPanicArticle,
    NewsAPIArticle,
    GrokPost,
)
from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.cryptopanic_client import CryptoPanicClient
from src.phase1_detector.news_aggregation.reddit_client import RedditClient
from src.phase1_detector.news_aggregation.newsapi_client import NewsAPIClient
from src.phase1_detector.news_aggregation.grok_client import GrokClient
from src.phase1_detector.news_aggregation.aggregator import NewsAggregator

__all__ = [
    # Models
    "NewsArticle",
    "RedditPost",
    "CryptoPanicArticle",
    "NewsAPIArticle",
    "GrokPost",
    # Clients
    "NewsClient",
    "CryptoPanicClient",
    "RedditClient",
    "NewsAPIClient",
    "GrokClient",
    # Aggregator
    "NewsAggregator",
]
