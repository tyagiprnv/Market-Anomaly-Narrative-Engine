"""Unit tests for news aggregation module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import os

# Set required environment variables for tests
os.environ["DATABASE__PASSWORD"] = "test_password"
os.environ["NEWS__CRYPTOPANIC_API_KEY"] = "test_crypto_key"
os.environ["NEWS__REDDIT_CLIENT_ID"] = "test_reddit_id"
os.environ["NEWS__REDDIT_CLIENT_SECRET"] = "test_reddit_secret"

from src.phase1_detector.news_aggregation import (
    NewsArticle,
    CryptoPanicClient,
    RedditClient,
    NewsAPIClient,
    NewsAggregator,
    CryptoPanicArticle,
    RedditPost,
    NewsAPIArticle,
)


# Mock data
MOCK_CRYPTOPANIC_RESPONSE = {
    "results": [
        {
            "id": 1234,
            "title": "Bitcoin reaches new high",
            "url": "https://example.com/btc-high",
            "published_at": "2024-01-15T12:00:00Z",
            "source": {"title": "CoinDesk"},
            "currencies": [{"code": "BTC"}],
            "kind": "news",
            "domain": "example.com",
            "votes": {"positive": 10, "negative": 2},
        }
    ]
}


MOCK_REDDIT_POST = Mock(
    id="abc123",
    title="Bitcoin discussion",
    selftext="Discussing BTC price movements",
    url="https://reddit.com/r/Bitcoin/abc123",
    score=100,
    num_comments=25,
    author="crypto_user",
    created_utc=datetime.now(timezone.utc).timestamp(),
    permalink="/r/Bitcoin/abc123",
)


MOCK_NEWSAPI_RESPONSE = {
    "status": "ok",
    "articles": [
        {
            "title": "Ethereum update",
            "url": "https://example.com/eth-update",
            "publishedAt": "2024-01-15T12:00:00Z",
            "source": {"name": "Bloomberg"},
            "author": "John Doe",
            "description": "Major Ethereum network upgrade",
            "content": "Full article content...",
        }
    ],
}


class TestNewsArticleModels:
    """Test Pydantic models for news articles."""

    def test_news_article_creation(self):
        """Test creating a NewsArticle."""
        article = NewsArticle(
            source="cryptopanic",
            title="Test article",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
            summary="Test summary",
            symbols=["BTC-USD"],
        )
        assert article.source == "cryptopanic"
        assert article.title == "Test article"
        assert "BTC-USD" in article.symbols

    def test_cryptopanic_article_conversion(self):
        """Test converting CryptoPanic article to NewsArticle."""
        crypto_article = CryptoPanicArticle(
            id=1234,
            title="Bitcoin news",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
            currencies=[{"code": "BTC"}],
            votes={"positive": 10, "negative": 2},
        )
        news_article = crypto_article.to_news_article()
        assert news_article.source == "cryptopanic"
        assert "BTC" in news_article.symbols
        assert news_article.sentiment is not None
        assert -1 <= news_article.sentiment <= 1

    def test_reddit_post_conversion(self):
        """Test converting Reddit post to NewsArticle."""
        reddit_post = RedditPost(
            post_id="abc123",
            subreddit="CryptoCurrency",
            title="Crypto discussion",
            selftext="Discussion content",
            url="https://reddit.com/r/CryptoCurrency/abc123",
            score=100,
            num_comments=25,
            author="user",
            created_utc=datetime.now(timezone.utc),
            permalink="/r/CryptoCurrency/abc123",
        )
        news_article = reddit_post.to_news_article(symbols=["BTC-USD"])
        assert news_article.source == "reddit"
        assert "BTC-USD" in news_article.symbols

    def test_newsapi_article_conversion(self):
        """Test converting NewsAPI article to NewsArticle."""
        newsapi_article = NewsAPIArticle(
            title="Ethereum news",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
            source_name="Bloomberg",
            description="Ethereum update",
        )
        news_article = newsapi_article.to_news_article(symbols=["ETH-USD"])
        assert news_article.source == "newsapi"
        assert "ETH-USD" in news_article.symbols


class TestCryptoPanicClient:
    """Test CryptoPanic API client."""

    @pytest.mark.asyncio
    async def test_get_news_success(self):
        """Test successful news fetching from CryptoPanic."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_CRYPTOPANIC_RESPONSE
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            async with CryptoPanicClient(api_key="test_key") as client:
                articles = await client.get_news(symbols=["BTC-USD"])

                assert len(articles) > 0
                assert articles[0].source == "cryptopanic"
                assert "BTC" in articles[0].symbols

    @pytest.mark.asyncio
    async def test_get_news_without_api_key(self):
        """Test that missing API key raises ValueError."""
        client = CryptoPanicClient(api_key="")
        with pytest.raises(ValueError, match="API key is required"):
            await client.get_news()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with valid API."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            async with CryptoPanicClient(api_key="test_key") as client:
                is_healthy = await client.health_check()
                assert is_healthy is True

    def test_source_name(self):
        """Test source name property."""
        client = CryptoPanicClient(api_key="test_key")
        assert client.source_name == "cryptopanic"


class TestRedditClient:
    """Test Reddit API client."""

    @pytest.mark.asyncio
    async def test_get_news_success(self):
        """Test successful news fetching from Reddit."""
        with patch("praw.Reddit") as mock_reddit:
            # Mock subreddit and posts
            mock_subreddit = Mock()
            mock_subreddit.hot.return_value = [MOCK_REDDIT_POST]
            mock_reddit.return_value.subreddit.return_value = mock_subreddit

            client = RedditClient(
                client_id="test_id",
                client_secret="test_secret",
            )

            articles = await client.get_news(symbols=["BTC"])

            assert len(articles) > 0
            assert articles[0].source == "reddit"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with valid credentials."""
        with patch("praw.Reddit") as mock_reddit:
            mock_subreddit = Mock()
            mock_subreddit.id = "test_id"
            mock_reddit.return_value.subreddit.return_value = mock_subreddit

            client = RedditClient(
                client_id="test_id",
                client_secret="test_secret",
            )

            is_healthy = await client.health_check()
            assert is_healthy is True

    def test_source_name(self):
        """Test source name property."""
        client = RedditClient(client_id="test_id", client_secret="test_secret")
        assert client.source_name == "reddit"


class TestNewsAPIClient:
    """Test NewsAPI client."""

    @pytest.mark.asyncio
    async def test_get_news_success(self):
        """Test successful news fetching from NewsAPI."""
        with patch("newsapi.NewsApiClient.get_everything") as mock_get:
            mock_get.return_value = MOCK_NEWSAPI_RESPONSE

            client = NewsAPIClient(api_key="test_key")
            articles = await client.get_news(symbols=["ETH-USD"])

            assert len(articles) > 0
            assert articles[0].source == "newsapi"

    @pytest.mark.asyncio
    async def test_get_news_without_api_key(self):
        """Test that missing API key raises ValueError."""
        client = NewsAPIClient(api_key="")
        with pytest.raises(ValueError, match="API key is required"):
            await client.get_news()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with valid API."""
        with patch("newsapi.NewsApiClient.get_everything") as mock_get:
            mock_get.return_value = {"status": "ok"}

            client = NewsAPIClient(api_key="test_key")
            is_healthy = await client.health_check()
            assert is_healthy is True

    def test_source_name(self):
        """Test source name property."""
        client = NewsAPIClient(api_key="test_key")
        assert client.source_name == "newsapi"


class TestNewsAggregator:
    """Test NewsAggregator."""

    @pytest.mark.asyncio
    async def test_get_news_for_anomaly(self):
        """Test fetching news for an anomaly with time window."""
        # Create aggregator with mocked clients
        with patch(
            "src.phase1_detector.news_aggregation.aggregator.CryptoPanicClient"
        ) as MockCrypto, patch(
            "src.phase1_detector.news_aggregation.aggregator.RedditClient"
        ) as MockReddit:

            # Mock client instances
            mock_crypto_client = AsyncMock()
            mock_crypto_client.get_news.return_value = [
                NewsArticle(
                    source="cryptopanic",
                    title="BTC news",
                    url="https://example.com",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                )
            ]
            MockCrypto.return_value = mock_crypto_client

            mock_reddit_client = AsyncMock()
            mock_reddit_client.get_news.return_value = [
                NewsArticle(
                    source="reddit",
                    title="BTC discussion",
                    url="https://reddit.com",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                )
            ]
            MockReddit.return_value = mock_reddit_client

            # Create aggregator
            aggregator = NewsAggregator(
                cryptopanic_key="test_key",
                reddit_client_id="test_id",
                reddit_client_secret="test_secret",
            )

            # Get news for anomaly
            anomaly_time = datetime.now(timezone.utc)
            articles = await aggregator.get_news_for_anomaly(
                symbols=["BTC-USD"],
                anomaly_time=anomaly_time,
                window_minutes=30,
            )

            assert len(articles) >= 2
            # Check that articles have timing tags
            assert all(hasattr(a, "timing_tag") for a in articles)

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate URLs are removed."""
        with patch(
            "src.phase1_detector.news_aggregation.aggregator.CryptoPanicClient"
        ) as MockCrypto:

            # Mock client with duplicate articles
            mock_client = AsyncMock()
            mock_client.get_news.return_value = [
                NewsArticle(
                    source="cryptopanic",
                    title="BTC news",
                    url="https://example.com/same",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                ),
                NewsArticle(
                    source="cryptopanic",
                    title="BTC news duplicate",
                    url="https://example.com/same",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                ),
            ]
            MockCrypto.return_value = mock_client

            aggregator = NewsAggregator(cryptopanic_key="test_key")

            articles = await aggregator.get_news(symbols=["BTC-USD"])

            # Should only have one article (deduplicated)
            assert len(articles) == 1

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check of all sources."""
        with patch(
            "src.phase1_detector.news_aggregation.aggregator.CryptoPanicClient"
        ) as MockCrypto:

            mock_client = AsyncMock()
            mock_client.health_check.return_value = True
            mock_client.source_name = "cryptopanic"
            MockCrypto.return_value = mock_client

            aggregator = NewsAggregator(cryptopanic_key="test_key")

            health = await aggregator.health_check()

            assert "cryptopanic" in health
            assert health["cryptopanic"] is True
