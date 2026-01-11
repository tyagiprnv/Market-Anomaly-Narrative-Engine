"""CryptoPanic API client for cryptocurrency news."""

import httpx
from datetime import datetime
from typing import Sequence

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle, CryptoPanicArticle


class CryptoPanicClient(NewsClient):
    """CryptoPanic API client.

    CryptoPanic aggregates crypto news from various sources and provides
    sentiment signals from community voting.

    API Documentation: https://cryptopanic.com/developers/api/
    """

    BASE_URL = "https://cryptopanic.com/api/v1"

    def __init__(self, api_key: str, timeout: int = 10):
        """Initialize CryptoPanic client.

        Args:
            api_key: CryptoPanic API key (get from https://cryptopanic.com/developers/api/)
            timeout: Request timeout in seconds
        """
        super().__init__(api_key=api_key)
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get news from CryptoPanic API.

        Args:
            symbols: Crypto symbols (e.g., ['BTC', 'ETH']). CryptoPanic uses currency codes.
            start_time: Not directly supported, will filter results
            end_time: Not directly supported, will filter results
            limit: Maximum articles to return (API supports up to 100)

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If API key is invalid
            ConnectionError: If API request fails
        """
        if not self.api_key:
            raise ValueError("CryptoPanic API key is required")

        # Build query parameters
        params = {
            "auth_token": self.api_key,
            "kind": "news",  # Only news articles, not media
            "filter": "hot",  # Hot news (trending)
        }

        # Add currency filter if symbols provided
        if symbols:
            # CryptoPanic uses currency codes (BTC, ETH) not trading pairs
            currencies = [s.split("-")[0] if "-" in s else s for s in symbols]
            params["currencies"] = ",".join(currencies)

        try:
            response = await self._client.get(f"{self.BASE_URL}/posts/", params=params)
            response.raise_for_status()
            data = response.json()

            if "results" not in data:
                raise ValueError(f"Unexpected API response: {data}")

            # Parse articles
            articles = []
            for item in data["results"][:limit]:
                try:
                    # Parse published_at timestamp
                    published_at = datetime.fromisoformat(
                        item["published_at"].replace("Z", "+00:00")
                    )

                    # Filter by time window if specified
                    if start_time and published_at < start_time:
                        continue
                    if end_time and published_at > end_time:
                        continue

                    crypto_article = CryptoPanicArticle(
                        id=item["id"],
                        title=item["title"],
                        url=item["url"],
                        published_at=published_at,
                        source_title=item.get("source", {}).get("title"),
                        currencies=item.get("currencies", []),
                        kind=item.get("kind"),
                        domain=item.get("domain"),
                        votes=item.get("votes"),
                    )
                    articles.append(crypto_article.to_news_article())
                except (KeyError, ValueError) as e:
                    # Skip malformed articles
                    continue

            return articles

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid CryptoPanic API key")
            raise ConnectionError(f"CryptoPanic API error: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to CryptoPanic: {e}")

    async def health_check(self) -> bool:
        """Check if CryptoPanic API is reachable.

        Returns:
            True if API is healthy, False otherwise
        """
        if not self.api_key:
            return False

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/posts/",
                params={"auth_token": self.api_key, "filter": "hot"},
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'cryptopanic'
        """
        return "cryptopanic"
