"""Unit tests for news aggregation module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import os

# Set required environment variables for tests
os.environ["DATABASE__PASSWORD"] = "test_password"
os.environ["NEWS__CRYPTOPANIC_API_KEY"] = "test_crypto_key"

from src.phase1_detector.news_aggregation import (
    NewsArticle,
    CryptoPanicClient,
    NewsAPIClient,
    NewsAggregator,
    CryptoPanicArticle,
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
        ) as MockCrypto:

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

            # Create aggregator
            aggregator = NewsAggregator(
                cryptopanic_key="test_key",
            )

            # Get news for anomaly
            anomaly_time = datetime.now(timezone.utc)
            articles = await aggregator.get_news_for_anomaly(
                symbols=["BTC-USD"],
                anomaly_time=anomaly_time,
                window_minutes=30,
            )

            assert len(articles) >= 1
            # Check that articles have timing tags
            assert all(hasattr(a, "timing_tag") for a in articles)

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate URLs are removed."""
        with patch(
            "src.phase1_detector.news_aggregation.aggregator.HistoricalReplayClient"
        ) as MockReplay:

            # Mock client with duplicate articles
            mock_replay_client = AsyncMock()
            mock_replay_client.get_news.return_value = [
                NewsArticle(
                    source="replay",
                    title="BTC news",
                    url="https://example.com/same",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                ),
                NewsArticle(
                    source="replay",
                    title="BTC news duplicate",
                    url="https://example.com/same",
                    published_at=datetime.now(timezone.utc),
                    symbols=["BTC"],
                ),
            ]
            MockReplay.return_value = mock_replay_client

            # Use replay mode to avoid real API clients
            aggregator = NewsAggregator(mode="replay")

            articles = await aggregator.get_news(symbols=["BTC-USD"])

            # Should only have one article (deduplicated)
            assert len(articles) == 1

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check of all sources."""
        with patch(
            "src.phase1_detector.news_aggregation.aggregator.CryptoPanicClient"
        ) as MockCrypto, patch(
            "src.phase1_detector.news_aggregation.aggregator.RSSFeedClient"
        ) as MockRSS:

            mock_crypto_client = AsyncMock()
            mock_crypto_client.health_check.return_value = True
            mock_crypto_client.source_name = "cryptopanic"
            MockCrypto.return_value = mock_crypto_client

            mock_rss_client = AsyncMock()
            mock_rss_client.health_check.return_value = True
            mock_rss_client.source_name = "rss"
            MockRSS.return_value = mock_rss_client

            aggregator = NewsAggregator(cryptopanic_key="test_key")

            health = await aggregator.health_check()

            assert "cryptopanic" in health
            assert health["cryptopanic"] is True
            assert "rss" in health
            assert health["rss"] is True
