"""News aggregator combining multiple news sources."""

import asyncio
from datetime import datetime, timedelta
from typing import Sequence

from config.settings import settings
from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.cryptopanic_client import CryptoPanicClient
from src.phase1_detector.news_aggregation.reddit_client import RedditClient
from src.phase1_detector.news_aggregation.newsapi_client import NewsAPIClient
from src.phase1_detector.news_aggregation.models import NewsArticle


class NewsAggregator:
    """Aggregates news from multiple sources for anomaly detection.

    Combines CryptoPanic, Reddit, and NewsAPI to provide comprehensive
    coverage of crypto-related news within specified time windows.

    This is the main entry point for Phase 1 news aggregation.
    """

    def __init__(
        self,
        cryptopanic_key: str | None = None,
        reddit_client_id: str | None = None,
        reddit_client_secret: str | None = None,
        newsapi_key: str | None = None,
    ):
        """Initialize news aggregator with API credentials.

        Args:
            cryptopanic_key: CryptoPanic API key (defaults to settings)
            reddit_client_id: Reddit client ID (defaults to settings)
            reddit_client_secret: Reddit client secret (defaults to settings)
            newsapi_key: NewsAPI key (defaults to settings)
        """
        self.clients: list[NewsClient] = []

        # Initialize CryptoPanic client
        crypto_key = cryptopanic_key or settings.news.cryptopanic_api_key
        if crypto_key:
            self.clients.append(CryptoPanicClient(api_key=crypto_key))

        # Initialize Reddit client
        reddit_id = reddit_client_id or settings.news.reddit_client_id
        reddit_secret = reddit_client_secret or settings.news.reddit_client_secret
        if reddit_id and reddit_secret:
            self.clients.append(
                RedditClient(
                    client_id=reddit_id,
                    client_secret=reddit_secret,
                    user_agent=settings.news.reddit_user_agent,
                )
            )

        # Initialize NewsAPI client (optional)
        news_key = newsapi_key or settings.news.newsapi_api_key
        if news_key:
            self.clients.append(NewsAPIClient(api_key=news_key))

        if not self.clients:
            raise ValueError("At least one news API key must be provided")

    async def get_news_for_anomaly(
        self,
        symbols: Sequence[str],
        anomaly_time: datetime,
        window_minutes: int | None = None,
        limit_per_source: int = 50,
    ) -> list[NewsArticle]:
        """Get news articles relevant to an anomaly.

        Fetches news from all configured sources within a time window
        around the anomaly detection time. This implements the causal
        filtering mentioned in the architecture - only news that could
        have actually caused the anomaly is included.

        Args:
            symbols: Crypto symbols (e.g., ['BTC-USD', 'ETH-USD'])
            anomaly_time: Time when anomaly was detected
            window_minutes: Time window (±minutes). Defaults to settings.
            limit_per_source: Max articles per source

        Returns:
            List of NewsArticle objects, sorted by published time (newest first)
        """
        window = window_minutes or settings.detection.news_window_minutes

        # Calculate time window (±window_minutes around anomaly)
        start_time = anomaly_time - timedelta(minutes=window)
        end_time = anomaly_time + timedelta(minutes=window)

        # Fetch from all sources concurrently
        tasks = []
        for client in self.clients:
            task = client.get_news(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                limit=limit_per_source,
            )
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine articles from all sources
        all_articles = []
        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other sources
                continue
            all_articles.extend(result)

        # Tag articles as pre_event or post_event
        for article in all_articles:
            time_diff = (article.published_at - anomaly_time).total_seconds() / 60
            if article.published_at < anomaly_time:
                article.timing_tag = "pre_event"
            else:
                article.timing_tag = "post_event"
            article.time_diff_minutes = time_diff

        # Sort by published time (newest first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = str(article.url) if article.url else article.title
            if url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        return unique_articles

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit_per_source: int = 50,
    ) -> list[NewsArticle]:
        """Get news articles from all sources.

        General method for fetching news without anomaly context.

        Args:
            symbols: Crypto symbols to filter by
            start_time: Start of time window
            end_time: End of time window
            limit_per_source: Max articles per source

        Returns:
            List of NewsArticle objects
        """
        # Fetch from all sources concurrently
        tasks = []
        for client in self.clients:
            task = client.get_news(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                limit=limit_per_source,
            )
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine articles from all sources
        all_articles = []
        for result in results:
            if isinstance(result, Exception):
                continue
            all_articles.extend(result)

        # Sort by published time (newest first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = str(article.url) if article.url else article.title
            if url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        return unique_articles

    async def health_check(self) -> dict[str, bool]:
        """Check health of all news sources.

        Returns:
            Dictionary mapping source names to health status
        """
        tasks = []
        sources = []

        for client in self.clients:
            tasks.append(client.health_check())
            sources.append(client.source_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            source: result if isinstance(result, bool) else False
            for source, result in zip(sources, results)
        }

    def __repr__(self) -> str:
        """String representation."""
        source_names = [client.source_name for client in self.clients]
        return f"<NewsAggregator(sources={source_names})>"
