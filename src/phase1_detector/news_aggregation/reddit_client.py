"""Reddit API client for cryptocurrency discussions."""

import asyncio
import praw
from datetime import datetime, timezone
from typing import Sequence

from src.phase1_detector.news_aggregation.news_client import NewsClient
from src.phase1_detector.news_aggregation.models import NewsArticle, RedditPost


class RedditClient(NewsClient):
    """Reddit API client using PRAW (Python Reddit API Wrapper).

    Fetches posts from crypto-related subreddits like r/CryptoCurrency,
    r/Bitcoin, r/ethereum, etc.

    API Documentation: https://praw.readthedocs.io/
    Reddit API: https://www.reddit.com/dev/api/
    """

    # Major crypto subreddits
    DEFAULT_SUBREDDITS = [
        "CryptoCurrency",
        "Bitcoin",
        "ethereum",
        "CryptoMarkets",
        "CryptoNews",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "MarketAnomalyEngine/0.1.0",
    ):
        """Initialize Reddit client.

        Args:
            client_id: Reddit app client ID
            client_secret: Reddit app client secret
            user_agent: User agent string for Reddit API

        To get credentials, create a Reddit app at:
        https://www.reddit.com/prefs/apps
        """
        super().__init__(api_key=None)
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

        # Initialize PRAW client
        self._reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    async def get_news(
        self,
        symbols: Sequence[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        subreddits: list[str] | None = None,
    ) -> list[NewsArticle]:
        """Get posts from crypto subreddits.

        Args:
            symbols: Crypto symbols to filter by (will search post titles/content)
            start_time: Start of time window
            end_time: End of time window
            limit: Maximum posts per subreddit
            subreddits: List of subreddits to search (defaults to DEFAULT_SUBREDDITS)

        Returns:
            List of NewsArticle objects

        Raises:
            ConnectionError: If Reddit API request fails
        """
        subreddits_list = subreddits or self.DEFAULT_SUBREDDITS
        all_posts = []

        # PRAW is synchronous, run in executor to avoid blocking
        loop = asyncio.get_event_loop()

        for subreddit_name in subreddits_list:
            try:
                subreddit = self._reddit.subreddit(subreddit_name)

                # Fetch hot posts (most engaging recent content)
                # We use "hot" instead of "new" to get more relevant, upvoted content
                posts = await loop.run_in_executor(
                    None, lambda: list(subreddit.hot(limit=limit))
                )

                for post in posts:
                    try:
                        # Convert timestamp
                        created_utc = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)

                        # Filter by time window
                        if start_time and created_utc < start_time:
                            continue
                        if end_time and created_utc > end_time:
                            continue

                        # Filter by symbols if specified
                        if symbols:
                            # Check if any symbol is mentioned in title or selftext
                            text = f"{post.title} {post.selftext or ''}".upper()
                            matching_symbols = [s for s in symbols if s.upper() in text]
                            if not matching_symbols:
                                continue
                        else:
                            matching_symbols = []

                        reddit_post = RedditPost(
                            post_id=post.id,
                            subreddit=subreddit_name,
                            title=post.title,
                            selftext=post.selftext,
                            url=post.url,
                            score=post.score,
                            num_comments=post.num_comments,
                            author=str(post.author),
                            created_utc=created_utc,
                            permalink=post.permalink,
                        )

                        all_posts.append(reddit_post.to_news_article(symbols=matching_symbols))

                    except Exception as e:
                        # Skip malformed posts
                        continue

            except Exception as e:
                # Skip problematic subreddits but continue with others
                continue

        # Sort by published time (newest first)
        all_posts.sort(key=lambda x: x.published_at, reverse=True)

        return all_posts[:limit]

    async def health_check(self) -> bool:
        """Check if Reddit API is reachable.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            # Try to access r/CryptoCurrency (always exists)
            await loop.run_in_executor(
                None, lambda: self._reddit.subreddit("CryptoCurrency").id
            )
            return True
        except:
            return False

    @property
    def source_name(self) -> str:
        """Get source name.

        Returns:
            'reddit'
        """
        return "reddit"
