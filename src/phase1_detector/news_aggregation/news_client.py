"""Abstract base class for news API clients."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from src.phase1_detector.news_aggregation.models import NewsArticle


class NewsClient(ABC):
    """Abstract base class for news API clients.

    All news clients (CryptoPanic, Reddit, NewsAPI) should inherit from this class
    and implement the required methods.
    """

    def __init__(self, api_key: str | None = None, **kwargs):
        """Initialize the news client.

        Args:
            api_key: API key for the news service
            **kwargs: Additional client-specific configuration
        """
        self.api_key = api_key

    @abstractmethod
    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get news articles for specified symbols and time range.

        Args:
            symbols: List of crypto symbols to filter by (e.g., ['BTC', 'ETH'])
            start_time: Start of time window (inclusive)
            end_time: End of time window (inclusive)
            limit: Maximum number of articles to return

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If API request fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the news API is reachable and healthy.

        Returns:
            True if API is healthy, False otherwise
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of this news source.

        Returns:
            Source name (e.g., 'cryptopanic', 'reddit', 'newsapi')
        """
        pass
