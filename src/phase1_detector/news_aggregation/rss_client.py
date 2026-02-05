"""RSS feed client for cryptocurrency news aggregation."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Sequence

import feedparser
import httpx
from feedparser import FeedParserDict

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle
from src.phase1_detector.news_aggregation.sentiment import extract_sentiment

logger = logging.getLogger(__name__)


class RSSFeedClient(NewsClient):
    """RSS feed client for cryptocurrency news sources.

    Fetches and parses RSS feeds from major crypto news outlets:
    - CoinDesk
    - Cointelegraph
    - Decrypt
    - Bitcoin Magazine
    - The Block

    All sources are free and do not require API keys.
    """

    # Default RSS feed URLs (all free)
    DEFAULT_FEEDS = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
        "https://bitcoinmagazine.com/feed",
        "https://www.theblock.co/rss.xml",
    ]

    def __init__(
        self,
        rss_feeds: list[str] | None = None,
        timeout: int = 30,
        user_agent: str = "MarketAnomalyEngine/0.1.0",
    ):
        """Initialize RSS feed client.

        Args:
            rss_feeds: List of RSS feed URLs (defaults to DEFAULT_FEEDS)
            timeout: HTTP request timeout in seconds
            user_agent: User agent string for HTTP requests
        """
        super().__init__(api_key=None)
        self.rss_feeds = rss_feeds or self.DEFAULT_FEEDS
        self.timeout = timeout
        self.user_agent = user_agent

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get news articles from RSS feeds.

        Args:
            symbols: Crypto symbols to filter by (e.g., ['BTC-USD', 'ETH-USD'])
            start_time: Start of time window (inclusive)
            end_time: End of time window (inclusive)
            limit: Maximum number of articles to return

        Returns:
            List of NewsArticle objects sorted by published time (newest first)

        Raises:
            ConnectionError: If all RSS feeds fail to fetch
        """
        all_articles = []
        successful_feeds = 0

        # Fetch all feeds concurrently
        tasks = [self._fetch_feed(feed_url) for feed_url in self.rss_feeds]
        feed_results = await asyncio.gather(*tasks, return_exceptions=True)

        for feed_url, result in zip(self.rss_feeds, feed_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch RSS feed {feed_url}: {result}")
                continue

            try:
                feed = feedparser.parse(result)
                successful_feeds += 1

                for entry in feed.entries:
                    try:
                        article = self._parse_entry(entry, symbols)
                        if article is None:
                            continue

                        # Apply time window filter
                        if start_time and article.published_at < start_time:
                            continue
                        if end_time and article.published_at > end_time:
                            continue

                        all_articles.append(article)

                    except Exception as e:
                        # Skip malformed entries
                        logger.debug(f"Failed to parse RSS entry: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Failed to parse feed {feed_url}: {e}")
                continue

        if successful_feeds == 0:
            raise ConnectionError("All RSS feeds failed to fetch")

        # Sort by published time (newest first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Apply limit
        return all_articles[:limit]

    async def _fetch_feed(self, feed_url: str) -> str:
        """Fetch RSS feed content via HTTP.

        Args:
            feed_url: RSS feed URL to fetch

        Returns:
            Raw RSS feed XML/content as string

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                feed_url,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    def _parse_entry(
        self, entry: FeedParserDict, symbols: Sequence[str] | None
    ) -> NewsArticle | None:
        """Parse RSS feed entry into NewsArticle.

        Args:
            entry: feedparser entry dict
            symbols: Symbols to filter by (checks title and summary)

        Returns:
            NewsArticle if entry matches filters, None otherwise
        """
        # Extract required fields
        title = entry.get("title", "").strip()
        if not title:
            return None

        link = entry.get("link", "")
        if not link:
            return None

        # Parse published date
        published_at = self._parse_published_date(entry)
        if published_at is None:
            return None

        # Extract summary/description
        summary = entry.get("summary") or entry.get("description") or entry.get("content")
        if isinstance(summary, list):
            summary = summary[0].get("value") if summary else None
        if summary and len(summary) > 500:
            summary = summary[:497] + "..."

        # Match symbols if specified, but DON'T filter out non-matching articles
        # Rationale: General crypto news (e.g., "Fed raises rates") affects all assets
        # The Journalist agent will determine relevance during narrative generation
        matching_symbols = []
        if symbols:
            text = f"{title} {summary or ''}".upper()
            # Broader matching: "BTC-USD" matches "BTC", "BITCOIN", etc.
            symbol_keywords = []
            for s in symbols:
                base = s.split("-")[0]  # "BTC" from "BTC-USD"
                symbol_keywords.extend([s.upper(), base])
                # Add common names
                if base == "BTC":
                    symbol_keywords.extend(["BITCOIN"])
                elif base == "ETH":
                    symbol_keywords.extend(["ETHEREUM"])
                elif base == "DOGE":
                    symbol_keywords.extend(["DOGECOIN"])
                elif base == "SOL":
                    symbol_keywords.extend(["SOLANA"])

            matching_symbols = [s for s in symbols if any(kw in text for kw in symbol_keywords)]
            # Don't filter out articles - keep all crypto news

        # Extract sentiment from title and summary
        sentiment = extract_sentiment(title, summary)

        return NewsArticle(
            source="rss",
            title=title,
            url=link,
            published_at=published_at,
            summary=summary,
            sentiment=sentiment,
            symbols=matching_symbols,
        )

    def _parse_published_date(self, entry: FeedParserDict) -> datetime | None:
        """Parse published date from RSS entry.

        Args:
            entry: feedparser entry dict

        Returns:
            datetime object with UTC timezone, or None if parsing fails
        """
        # Try multiple date fields (RSS 2.0, Atom, etc.)
        date_fields = ["published_parsed", "updated_parsed", "created_parsed"]

        for field in date_fields:
            time_struct = entry.get(field)
            if time_struct:
                try:
                    # Convert time.struct_time to datetime
                    dt = datetime(*time_struct[:6], tzinfo=timezone.utc)
                    return dt
                except (ValueError, TypeError):
                    continue

        # Try parsing date strings as fallback
        date_string_fields = ["published", "updated", "created"]
        for field in date_string_fields:
            date_str = entry.get(field)
            if date_str:
                try:
                    # feedparser usually handles date parsing, but handle edge cases
                    from email.utils import parsedate_to_datetime

                    dt = parsedate_to_datetime(date_str)
                    # Ensure UTC timezone
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except (ValueError, TypeError):
                    continue

        return None

    async def health_check(self) -> bool:
        """Check if RSS feeds are accessible.

        Returns:
            True if at least one feed is reachable, False otherwise
        """
        try:
            # Test first feed only (faster check)
            if not self.rss_feeds:
                return False

            await self._fetch_feed(self.rss_feeds[0])
            return True
        except:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'rss'
        """
        return "rss"
