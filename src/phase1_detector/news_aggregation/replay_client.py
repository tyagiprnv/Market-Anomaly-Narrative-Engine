"""Historical replay client for deterministic news aggregation."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle

logger = logging.getLogger(__name__)


class HistoricalReplayClient(NewsClient):
    """Historical replay client for deterministic testing and demos.

    Loads pre-recorded news data from JSON files to enable:
    - Deterministic testing (replay produces identical results)
    - Cost-free demos (no API calls)
    - Known event validation (test against major crypto events)

    Dataset format: datasets/news/{symbol}_{date}.json
    Example: datasets/news/BTC-USD_2024-03-14.json

    JSON schema:
    {
        "symbol": "BTC-USD",
        "date": "2024-03-14",
        "articles": [
            {
                "source": "coindesk",
                "title": "...",
                "url": "...",
                "published_at": "2024-03-14T14:30:00Z",
                "sentiment": 0.8,
                "summary": "...",
                "symbols": ["BTC-USD"]
            }
        ]
    }
    """

    def __init__(self, dataset_path: str = "datasets/news/"):
        """Initialize historical replay client.

        Args:
            dataset_path: Path to directory containing news JSON files
        """
        super().__init__(api_key=None)
        self.dataset_path = Path(dataset_path)
        self._cache: dict[str, list[NewsArticle]] = {}

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get news articles from historical replay datasets.

        Args:
            symbols: Crypto symbols to filter by
            start_time: Start of time window (inclusive)
            end_time: End of time window (inclusive)
            limit: Maximum number of articles to return

        Returns:
            List of NewsArticle objects sorted by published time (newest first)

        Raises:
            FileNotFoundError: If no datasets found for requested time range
            ValueError: If dataset JSON is malformed
        """
        if not symbols:
            raise ValueError("Historical replay requires explicit symbols")

        # Load datasets for requested symbols and time range
        all_articles = []

        for symbol in symbols:
            articles = await self._load_articles_for_symbol(symbol, start_time, end_time)
            all_articles.extend(articles)

        # Apply time window filter
        filtered_articles = []
        for article in all_articles:
            if start_time and article.published_at < start_time:
                continue
            if end_time and article.published_at > end_time:
                continue
            filtered_articles.append(article)

        # Sort by published time (newest first)
        filtered_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Apply limit
        return filtered_articles[:limit]

    async def _load_articles_for_symbol(
        self,
        symbol: str,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[NewsArticle]:
        """Load articles for a specific symbol from JSON datasets.

        Args:
            symbol: Crypto symbol (e.g., 'BTC-USD')
            start_time: Start of time window
            end_time: End of time window

        Returns:
            List of NewsArticle objects
        """
        # Check cache first
        cache_key = f"{symbol}_{start_time}_{end_time}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        articles = []

        # Find all JSON files for this symbol
        pattern = f"{symbol}_*.json"
        dataset_files = list(self.dataset_path.glob(pattern))

        if not dataset_files:
            logger.warning(f"No historical datasets found for symbol {symbol}")
            return []

        # Load articles from each file
        for dataset_file in dataset_files:
            try:
                with open(dataset_file, "r") as f:
                    data = json.load(f)

                # Validate dataset structure
                if "articles" not in data:
                    logger.warning(f"Invalid dataset format in {dataset_file}: missing 'articles'")
                    continue

                # Parse articles
                for article_data in data["articles"]:
                    try:
                        article = self._parse_article(article_data)
                        articles.append(article)
                    except Exception as e:
                        logger.debug(f"Failed to parse article in {dataset_file}: {e}")
                        continue

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {dataset_file}: {e}")
                continue
            except Exception as e:
                logger.error(f"Failed to load {dataset_file}: {e}")
                continue

        # Cache results
        self._cache[cache_key] = articles

        return articles

    def _parse_article(self, article_data: dict) -> NewsArticle:
        """Parse article dictionary into NewsArticle model.

        Args:
            article_data: Article data from JSON

        Returns:
            NewsArticle instance

        Raises:
            ValueError: If required fields are missing
        """
        # Parse published_at timestamp
        published_at_str = article_data.get("published_at")
        if not published_at_str:
            raise ValueError("Missing 'published_at' field")

        # Handle both ISO format and timestamp
        if isinstance(published_at_str, str):
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        else:
            published_at = datetime.fromtimestamp(published_at_str, tz=timezone.utc)

        # Ensure timezone aware
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)

        return NewsArticle(
            source=article_data.get("source", "replay"),
            title=article_data["title"],
            url=article_data.get("url"),
            published_at=published_at,
            summary=article_data.get("summary"),
            sentiment=article_data.get("sentiment"),
            symbols=article_data.get("symbols", []),
        )

    async def health_check(self) -> bool:
        """Check if dataset path exists and has files.

        Returns:
            True if dataset directory exists and contains JSON files, False otherwise
        """
        try:
            if not self.dataset_path.exists():
                return False

            # Check if any JSON files exist
            json_files = list(self.dataset_path.glob("*.json"))
            return len(json_files) > 0

        except Exception:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'replay'
        """
        return "replay"

    def clear_cache(self) -> None:
        """Clear the article cache."""
        self._cache.clear()
