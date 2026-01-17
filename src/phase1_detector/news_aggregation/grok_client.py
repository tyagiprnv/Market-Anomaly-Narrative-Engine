"""Grok API client for X/Twitter cryptocurrency data."""

import httpx
import logging
from datetime import datetime, timezone
from typing import Sequence

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle, GrokPost

logger = logging.getLogger(__name__)


class GrokClient(NewsClient):
    """Grok API client for X/Twitter data access.

    Uses xAI's Grok API with the x_search server-side tool to search
    X/Twitter posts for cryptocurrency discussions. Provides real-time
    social sentiment data from traders, influencers, and exchanges.

    API Documentation: https://docs.x.ai/docs/overview
    Free Tier: $25/month credits
    """

    BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-beta"  # Fast model optimized for tool use
    DEFAULT_TIMEOUT = 30  # Higher timeout due to tool calling
    MIN_ENGAGEMENT = 100  # Minimum likes for filtering
    FREE_TIER_LIMIT = 25.0  # Free tier dollar limit

    # Symbol to common name mapping for better search results
    SYMBOL_NAMES = {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "BNB": "Binance Coin",
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
        "ETC": "Ethereum Classic",
        "XLM": "Stellar",
        "ALGO": "Algorand",
        "VET": "VeChain",
        "ICP": "Internet Computer",
        "FIL": "Filecoin",
    }

    def __init__(
        self,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT,
        model: str = DEFAULT_MODEL,
        min_engagement: int = MIN_ENGAGEMENT,
    ):
        """Initialize Grok API client.

        Args:
            api_key: xAI API key (get from https://console.x.ai/)
            timeout: Request timeout in seconds (default: 30)
            model: Grok model to use (default: grok-beta)
            min_engagement: Minimum likes for post filtering (default: 100)
        """
        super().__init__(api_key=api_key)
        self.timeout = timeout
        self.model = model
        self.min_engagement = min_engagement
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        # Usage tracking for budget enforcement
        self._cumulative_cost = 0.0
        self._request_count = 0

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()

    def _build_search_query(self, symbols: Sequence[str] | None = None) -> str:
        """Build search query for X/Twitter posts.

        Constructs queries targeting crypto symbols with relevant keywords
        to capture price movement discussions.

        Args:
            symbols: Crypto symbols (e.g., ['BTC-USD', 'ETH-USD'])

        Returns:
            Search query string optimized for x_search
        """
        if not symbols or len(symbols) == 0:
            # Generic crypto query if no specific symbols
            return "(cryptocurrency OR crypto) (surge OR crash OR rally OR pump OR dump OR breakout)"

        # Build query with symbols and their common names
        symbol_parts = []
        for symbol in symbols[:3]:  # Limit to 3 symbols to avoid overly long queries
            # Extract currency code (e.g., 'BTC' from 'BTC-USD')
            currency = symbol.split("-")[0] if "-" in symbol else symbol
            name = self.SYMBOL_NAMES.get(currency, currency)

            # Create OR clause for each symbol
            symbol_parts.append(f"({name} OR {currency})")

        # Combine with event keywords
        symbol_query = " OR ".join(symbol_parts)
        keywords = "(surge OR crash OR rally OR pump OR dump OR moon OR breakout OR dip)"

        return f"({symbol_query}) {keywords}"

    def _extract_posts_from_response(self, response_data: dict) -> list[GrokPost]:
        """Extract X/Twitter posts from Grok API response.

        Parses the tool call results from the chat completion response
        and converts them to GrokPost objects.

        Args:
            response_data: JSON response from Grok API

        Returns:
            List of GrokPost objects
        """
        posts = []

        try:
            # Extract tool calls from the assistant's response
            choices = response_data.get("choices", [])
            if not choices:
                logger.warning("No choices in Grok API response")
                return posts

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                logger.warning("No tool calls in Grok API response")
                return posts

            # Process x_search tool results
            for tool_call in tool_calls:
                if tool_call.get("function", {}).get("name") != "x_search":
                    continue

                # Parse tool call results (stored in function.arguments as JSON string)
                import json

                try:
                    results = json.loads(tool_call["function"]["arguments"])
                    search_results = results.get("results", [])

                    for result in search_results:
                        # Extract post data
                        post_id = result.get("id", result.get("post_id", ""))
                        if not post_id:
                            continue

                        # Parse timestamp
                        created_at_str = result.get("created_at")
                        if created_at_str:
                            try:
                                created_at = datetime.fromisoformat(
                                    created_at_str.replace("Z", "+00:00")
                                )
                            except ValueError:
                                # Fallback to current time if parsing fails
                                created_at = datetime.now(timezone.utc)
                        else:
                            created_at = datetime.now(timezone.utc)

                        post = GrokPost(
                            post_id=post_id,
                            author_handle=result.get("author_handle", result.get("author")),
                            text=result.get("text", result.get("content", "")),
                            url=result.get("url", f"https://x.com/i/web/status/{post_id}"),
                            created_at=created_at,
                            likes=result.get("likes", result.get("favorites", 0)),
                            retweets=result.get("retweets", 0),
                            replies=result.get("replies", result.get("reply_count", 0)),
                        )
                        posts.append(post)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool call arguments: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting posts from Grok response: {e}")

        return posts

    def _filter_posts(
        self,
        posts: list[GrokPost],
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[GrokPost]:
        """Filter posts by engagement, timing, and symbol matching.

        Applies user requirements:
        1. Minimum engagement threshold (100+ likes by default)
        2. Exclude retweets (original content only)
        3. Time window filtering
        4. Symbol matching verification

        Args:
            posts: List of GrokPost objects
            symbols: Crypto symbols to verify in post text
            start_time: Start of time window
            end_time: End of time window

        Returns:
            Filtered list of GrokPost objects
        """
        filtered = []

        for post in posts:
            # Filter 1: Minimum engagement (100+ likes)
            if post.likes < self.min_engagement:
                continue

            # Filter 2: Exclude retweets
            # Retweets typically start with "RT @" or have high retweet/likes ratio
            if post.text.startswith("RT @") or post.text.startswith("rt @"):
                continue

            # Additional retweet heuristic: if retweets > likes, likely a retweet
            if post.retweets > post.likes:
                continue

            # Filter 3: Time window
            if start_time and post.created_at < start_time:
                continue
            if end_time and post.created_at > end_time:
                continue

            # Filter 4: Symbol matching (optional verification)
            if symbols:
                # Check if any symbol appears in the post text
                text_upper = post.text.upper()
                symbol_found = False

                for symbol in symbols:
                    currency = symbol.split("-")[0] if "-" in symbol else symbol
                    name = self.SYMBOL_NAMES.get(currency, currency)

                    if currency.upper() in text_upper or name.upper() in text_upper:
                        symbol_found = True
                        break

                if not symbol_found:
                    continue

            filtered.append(post)

        return filtered

    def _track_usage(self, response_data: dict):
        """Track API usage for budget enforcement.

        Logs token usage and estimates cost based on xAI pricing:
        - Input: $0.20 per 1M tokens
        - Output: $0.50 per 1M tokens
        - X Search tool: ~$2.50-5 per 1K calls

        Args:
            response_data: JSON response from Grok API
        """
        try:
            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # Calculate cost (approximate)
            input_cost = (prompt_tokens / 1_000_000) * 0.20
            output_cost = (completion_tokens / 1_000_000) * 0.50
            tool_cost = 0.003  # Approximate cost per x_search call

            total_cost = input_cost + output_cost + tool_cost
            self._cumulative_cost += total_cost
            self._request_count += 1

            logger.info(
                f"Grok API usage: {prompt_tokens} in + {completion_tokens} out tokens, "
                f"cost: ${total_cost:.4f}, cumulative: ${self._cumulative_cost:.4f}"
            )

            # Warn at 80% of free tier
            if self._cumulative_cost >= self.FREE_TIER_LIMIT * 0.8:
                logger.warning(
                    f"Approaching free tier limit: ${self._cumulative_cost:.2f} / "
                    f"${self.FREE_TIER_LIMIT}"
                )

            # Hard stop at 100%
            if self._cumulative_cost >= self.FREE_TIER_LIMIT:
                raise ConnectionError(
                    f"Grok API free tier limit reached (${self.FREE_TIER_LIMIT}). "
                    "Please upgrade or wait for next billing cycle."
                )

        except KeyError as e:
            logger.warning(f"Could not track usage: {e}")

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Get X/Twitter posts using Grok API x_search tool.

        Searches for cryptocurrency discussions on X/Twitter within the
        specified time window. Applies engagement filtering (100+ likes)
        and excludes retweets.

        Args:
            symbols: Crypto symbols (e.g., ['BTC-USD', 'ETH-USD'])
            start_time: Start of time window (inclusive)
            end_time: End of time window (inclusive)
            limit: Maximum posts to return (default: 50)

        Returns:
            List of NewsArticle objects converted from GrokPost

        Raises:
            ValueError: If API key is invalid
            ConnectionError: If API request fails or budget exceeded
        """
        if not self.api_key:
            raise ValueError("Grok API key is required")

        # Build search query
        query = self._build_search_query(symbols)

        # Build chat completion request with x_search tool
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency market analyst. Search X/Twitter for relevant posts.",
                },
                {
                    "role": "user",
                    "content": f"Search X/Twitter for posts about: {query}. "
                    f"Find posts from the last 24 hours with high engagement.",
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "x_search",
                        "description": "Search X/Twitter posts",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query"},
                                "search_mode": {
                                    "type": "string",
                                    "enum": ["keyword", "semantic", "hybrid"],
                                    "description": "Search mode",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum results",
                                },
                            },
                            "required": ["query"],
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "x_search"}},
        }

        try:
            # Make API request
            response = await self._client.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Track usage
            self._track_usage(data)

            # Extract posts from response
            posts = self._extract_posts_from_response(data)

            # Apply filters (engagement, retweets, timing, symbols)
            filtered_posts = self._filter_posts(posts, symbols, start_time, end_time)

            # Convert to NewsArticle objects
            articles = []
            for post in filtered_posts[:limit]:
                try:
                    article = post.to_news_article(symbols=list(symbols) if symbols else None)
                    articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to convert post to article: {e}")
                    continue

            logger.info(
                f"Grok API returned {len(posts)} posts, filtered to {len(filtered_posts)}, "
                f"converted {len(articles)} to articles"
            )

            return articles

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid Grok API key")
            elif e.response.status_code == 429:
                raise ConnectionError("Grok API rate limit exceeded")
            raise ConnectionError(f"Grok API error: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Grok API: {e}")

    async def health_check(self) -> bool:
        """Check if Grok API is reachable.

        Uses the /models endpoint for a lightweight health check.

        Returns:
            True if API is healthy, False otherwise
        """
        if not self.api_key:
            return False

        try:
            response = await self._client.get(
                f"{self.BASE_URL}/models",
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'grok'
        """
        return "grok"

    @property
    def usage_stats(self) -> dict:
        """Get usage statistics.

        Returns:
            Dictionary with cumulative cost and request count
        """
        return {
            "cumulative_cost": self._cumulative_cost,
            "request_count": self._request_count,
            "free_tier_limit": self.FREE_TIER_LIMIT,
            "usage_percentage": (self._cumulative_cost / self.FREE_TIER_LIMIT) * 100,
        }
