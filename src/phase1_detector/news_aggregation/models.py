"""Pydantic models for news data."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class NewsArticle(BaseModel):
    """News article data from various sources.

    Attributes:
        source: News source (cryptopanic, reddit, newsapi)
        title: Article title
        url: Article URL (optional for Reddit posts)
        published_at: Publication timestamp
        summary: Article summary or content snippet
        sentiment: Optional sentiment score (-1 to 1, where -1 is bearish, 1 is bullish)
        symbols: List of crypto symbols mentioned in the article
        timing_tag: Whether article is pre_event or post_event (set by aggregator)
        time_diff_minutes: Minutes before/after anomaly (set by aggregator)
    """

    source: str
    title: str
    url: HttpUrl | str | None = None
    published_at: datetime
    summary: str | None = None
    sentiment: float | None = Field(None, ge=-1.0, le=1.0)
    symbols: list[str] = Field(default_factory=list)
    timing_tag: str | None = None
    time_diff_minutes: float | None = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class RedditPost(BaseModel):
    """Reddit post data specific to crypto discussions.

    Attributes:
        post_id: Reddit post ID
        subreddit: Subreddit name (e.g., 'CryptoCurrency', 'Bitcoin')
        title: Post title
        selftext: Post content (for text posts)
        url: Post URL
        score: Reddit score (upvotes - downvotes)
        num_comments: Number of comments
        author: Post author username
        created_utc: UTC timestamp
        permalink: Relative URL to the post
    """

    post_id: str
    subreddit: str
    title: str
    selftext: str | None = None
    url: str
    score: int
    num_comments: int
    author: str
    created_utc: datetime
    permalink: str

    def to_news_article(self, symbols: list[str] | None = None) -> NewsArticle:
        """Convert Reddit post to NewsArticle.

        Args:
            symbols: List of symbols to associate with this article

        Returns:
            NewsArticle instance
        """
        return NewsArticle(
            source="reddit",
            title=self.title,
            url=f"https://reddit.com{self.permalink}",
            published_at=self.created_utc,
            summary=self.selftext[:500] if self.selftext else None,
            symbols=symbols or [],
        )


class CryptoPanicArticle(BaseModel):
    """CryptoPanic API article data.

    Attributes:
        id: CryptoPanic article ID
        title: Article title
        url: Article URL
        published_at: Publication timestamp
        source_title: Original source (e.g., 'CoinDesk', 'Bloomberg')
        currencies: List of currency codes mentioned
        kind: Article kind (news, media)
        domain: Source domain
        votes: Voting data from CryptoPanic users
    """

    id: int
    title: str
    url: HttpUrl
    published_at: datetime
    source_title: str | None = None
    currencies: list[dict] = Field(default_factory=list)
    kind: str | None = None
    domain: str | None = None
    votes: dict | None = None

    def to_news_article(self) -> NewsArticle:
        """Convert CryptoPanic article to NewsArticle.

        Returns:
            NewsArticle instance
        """
        # Extract symbol codes from currencies
        symbols = [curr.get("code", "").upper() for curr in self.currencies if curr.get("code")]

        # Calculate sentiment from votes if available
        sentiment = None
        if self.votes:
            positive = self.votes.get("positive", 0)
            negative = self.votes.get("negative", 0)
            total = positive + negative
            if total > 0:
                sentiment = (positive - negative) / total

        return NewsArticle(
            source="cryptopanic",
            title=self.title,
            url=str(self.url),
            published_at=self.published_at,
            summary=f"Source: {self.source_title or self.domain}",
            sentiment=sentiment,
            symbols=symbols,
        )


class NewsAPIArticle(BaseModel):
    """NewsAPI article data.

    Attributes:
        title: Article title
        url: Article URL
        published_at: Publication timestamp
        source_name: Source name (e.g., 'Bloomberg', 'Reuters')
        author: Article author
        description: Article description
        content: Article content snippet
    """

    title: str
    url: HttpUrl
    published_at: datetime
    source_name: str | None = None
    author: str | None = None
    description: str | None = None
    content: str | None = None

    def to_news_article(self, symbols: list[str] | None = None) -> NewsArticle:
        """Convert NewsAPI article to NewsArticle.

        Args:
            symbols: List of symbols to associate with this article

        Returns:
            NewsArticle instance
        """
        summary = self.description or self.content
        if summary and len(summary) > 500:
            summary = summary[:497] + "..."

        return NewsArticle(
            source="newsapi",
            title=self.title,
            url=str(self.url),
            published_at=self.published_at,
            summary=summary,
            symbols=symbols or [],
        )


class GrokPost(BaseModel):
    """X/Twitter post from Grok API x_search tool.

    Attributes:
        post_id: Unique X/Twitter post ID
        author_handle: Author's X/Twitter handle (optional)
        text: Post content/text
        url: URL to the X/Twitter post
        created_at: Post creation timestamp
        likes: Number of likes (favorites)
        retweets: Number of retweets
        replies: Number of replies
    """

    post_id: str
    author_handle: str | None = None
    text: str
    url: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0

    def to_news_article(self, symbols: list[str] | None = None) -> NewsArticle:
        """Convert X/Twitter post to NewsArticle.

        Sentiment is calculated from engagement metrics:
        - Higher engagement (likes/total) = more positive sentiment
        - Normalized to range [-1, 1]
        - Formula: (likes / total_engagement) * 2 - 1

        Args:
            symbols: List of symbols to associate with this article

        Returns:
            NewsArticle instance
        """
        # Calculate engagement-based sentiment
        total_engagement = self.likes + self.retweets + self.replies
        if total_engagement > 0:
            # Normalize likes ratio to [-1, 1] range
            # Assumes likes are the primary positive signal
            sentiment = (self.likes / total_engagement) * 2 - 1
            # Clamp to valid range
            sentiment = max(-1.0, min(1.0, sentiment))
        else:
            sentiment = 0.0

        # Create summary with engagement stats
        summary = (
            f"{self.text[:300]}... "
            f"(Engagement: {self.likes} likes, {self.retweets} retweets, {self.replies} replies)"
        )

        return NewsArticle(
            source="grok",
            title=self.text[:100] if len(self.text) > 100 else self.text,
            url=self.url,
            published_at=self.created_at,
            summary=summary,
            sentiment=sentiment,
            symbols=symbols or [],
        )
