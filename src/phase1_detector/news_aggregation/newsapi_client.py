"""NewsAPI client for general cryptocurrency news."""

from datetime import datetime
from typing import Sequence
from newsapi import NewsApiClient
import asyncio

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle, NewsAPIArticle


class NewsAPIClient(NewsClient):
    """NewsAPI client for general crypto news from major outlets.

    NewsAPI aggregates news from major publications like Bloomberg, Reuters,
    CoinDesk, etc.

    API Documentation: https://newsapi.org/docs
    """

    def __init__(self, api_key: str):
        """Initialize NewsAPI client.

        Args:
            api_key: NewsAPI key (get from https://newsapi.org/)
        """
        super().__init__(api_key=api_key)
        self._client = NewsApiClient(api_key=api_key)

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get news from NewsAPI.

        Args:
            symbols: Crypto symbols to search for (e.g., ['BTC', 'ETH'])
            start_time: Start of time window
            end_time: End of time window (defaults to now)
            limit: Maximum articles to return (NewsAPI max is 100)

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If API key is invalid
            ConnectionError: If API request fails
        """
        if not self.api_key:
            raise ValueError("NewsAPI key is required")

        # Build search query from symbols
        if symbols:
            # Create query like: (Bitcoin OR BTC) AND (cryptocurrency OR crypto)
            symbol_names = []
            for symbol in symbols:
                base = symbol.split("-")[0] if "-" in symbol else symbol
                # Map common symbols to their names
                name_map = {
                    "BTC": "Bitcoin",
                    "ETH": "Ethereum",
                    "BNB": "Binance",
                    "SOL": "Solana",
                    "XRP": "Ripple",
                    "ADA": "Cardano",
                    "DOGE": "Dogecoin",
                    "AVAX": "Avalanche",
                    "DOT": "Polkadot",
                    "MATIC": "Polygon",
                    "LINK": "Chainlink",
                    "UNI": "Uniswap",
                    "ATOM": "Cosmos",
                    "LTC": "Litecoin",
                }
                name = name_map.get(base, base)
                symbol_names.append(f"({name} OR {base})")

            query = " OR ".join(symbol_names)
            query += " AND (cryptocurrency OR crypto)"
        else:
            # Default to general crypto news
            query = "cryptocurrency OR bitcoin OR ethereum OR crypto"

        # Format dates for NewsAPI (requires ISO 8601)
        from_date = start_time.isoformat() if start_time else None
        to_date = end_time.isoformat() if end_time else None

        try:
            # NewsAPI is synchronous, run in executor
            loop = asyncio.get_event_loop()

            # Use everything endpoint for comprehensive search
            response = await loop.run_in_executor(
                None,
                lambda: self._client.get_everything(
                    q=query,
                    from_param=from_date,
                    to=to_date,
                    language="en",
                    sort_by="publishedAt",  # Most recent first
                    page_size=min(limit, 100),  # API max is 100
                ),
            )

            if response["status"] != "ok":
                raise ValueError(f"NewsAPI error: {response.get('message', 'Unknown error')}")

            # Parse articles
            articles = []
            for item in response["articles"]:
                try:
                    # Parse published date
                    published_at = datetime.fromisoformat(
                        item["publishedAt"].replace("Z", "+00:00")
                    )

                    news_article = NewsAPIArticle(
                        title=item["title"],
                        url=item["url"],
                        published_at=published_at,
                        source_name=item["source"].get("name"),
                        author=item.get("author"),
                        description=item.get("description"),
                        content=item.get("content"),
                    )

                    # Extract symbols from content
                    matching_symbols = []
                    if symbols:
                        text = f"{item['title']} {item.get('description', '')}".upper()
                        matching_symbols = [s for s in symbols if s.upper() in text]

                    articles.append(news_article.to_news_article(symbols=matching_symbols))

                except (KeyError, ValueError):
                    # Skip malformed articles
                    continue

            return articles

        except Exception as e:
            if "apiKey" in str(e).lower():
                raise ValueError("Invalid NewsAPI key")
            raise ConnectionError(f"NewsAPI error: {e}")

    async def health_check(self) -> bool:
        """Check if NewsAPI is reachable.

        Returns:
            True if API is healthy, False otherwise
        """
        if not self.api_key:
            return False

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.get_everything(
                    q="test",
                    page_size=1,
                ),
            )
            return response["status"] == "ok"
        except:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'newsapi'
        """
        return "newsapi"
