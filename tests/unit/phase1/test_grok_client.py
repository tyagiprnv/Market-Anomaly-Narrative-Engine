"""Unit tests for Grok API client."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import json
import os

# Set required environment variables for tests
os.environ["DATABASE__PASSWORD"] = "test_password"
os.environ["NEWS__CRYPTOPANIC_API_KEY"] = "test_crypto_key"
os.environ["NEWS__REDDIT_CLIENT_ID"] = "test_reddit_id"
os.environ["NEWS__REDDIT_CLIENT_SECRET"] = "test_reddit_secret"

from src.phase1_detector.news_aggregation import GrokClient, GrokPost, NewsArticle


# Mock data
MOCK_GROK_POST_DATA = {
    "id": "1234567890",
    "author_handle": "@crypto_trader",
    "text": "Bitcoin just surged 5% in 10 minutes! This is huge for BTC holders. #Bitcoin #crypto",
    "url": "https://x.com/i/web/status/1234567890",
    "created_at": "2024-01-15T12:00:00Z",
    "likes": 150,
    "retweets": 25,
    "replies": 10,
}

MOCK_GROK_API_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "grok-beta",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "I found some relevant posts about Bitcoin.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "x_search",
                            "arguments": json.dumps(
                                {
                                    "results": [
                                        MOCK_GROK_POST_DATA,
                                        {
                                            "id": "9876543210",
                                            "author_handle": "@eth_whale",
                                            "text": "Ethereum breaking out! ETH looks strong. #Ethereum #crypto",
                                            "url": "https://x.com/i/web/status/9876543210",
                                            "created_at": "2024-01-15T12:05:00Z",
                                            "likes": 200,
                                            "retweets": 40,
                                            "replies": 15,
                                        },
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
}

MOCK_GROK_API_RESPONSE_LOW_ENGAGEMENT = {
    "id": "chatcmpl-456",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "grok-beta",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Found a post with low engagement.",
                "tool_calls": [
                    {
                        "id": "call_456",
                        "type": "function",
                        "function": {
                            "name": "x_search",
                            "arguments": json.dumps(
                                {
                                    "results": [
                                        {
                                            "id": "1111111111",
                                            "author_handle": "@small_account",
                                            "text": "Bitcoin is moving",
                                            "url": "https://x.com/i/web/status/1111111111",
                                            "created_at": "2024-01-15T12:00:00Z",
                                            "likes": 5,  # Below minimum engagement
                                            "retweets": 1,
                                            "replies": 0,
                                        }
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
}

MOCK_GROK_API_RESPONSE_RETWEET = {
    "id": "chatcmpl-789",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "grok-beta",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Found a retweet.",
                "tool_calls": [
                    {
                        "id": "call_789",
                        "type": "function",
                        "function": {
                            "name": "x_search",
                            "arguments": json.dumps(
                                {
                                    "results": [
                                        {
                                            "id": "2222222222",
                                            "author_handle": "@retweeter",
                                            "text": "RT @original: Bitcoin breaking news!",
                                            "url": "https://x.com/i/web/status/2222222222",
                                            "created_at": "2024-01-15T12:00:00Z",
                                            "likes": 150,
                                            "retweets": 500,  # High retweets indicate RT
                                            "replies": 5,
                                        }
                                    ]
                                }
                            ),
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
}


class TestGrokPost:
    """Test GrokPost model."""

    def test_grok_post_creation(self):
        """Test creating a GrokPost."""
        post = GrokPost(
            post_id="123456",
            author_handle="@trader",
            text="Bitcoin surge! BTC up 5%",
            url="https://x.com/i/web/status/123456",
            created_at=datetime.now(timezone.utc),
            likes=150,
            retweets=20,
            replies=10,
        )
        assert post.post_id == "123456"
        assert post.author_handle == "@trader"
        assert post.likes == 150
        assert post.retweets == 20
        assert post.replies == 10

    def test_grok_post_to_news_article(self):
        """Test converting GrokPost to NewsArticle."""
        post = GrokPost(
            post_id="123456",
            author_handle="@trader",
            text="Bitcoin surge! BTC up 5%",
            url="https://x.com/i/web/status/123456",
            created_at=datetime.now(timezone.utc),
            likes=150,
            retweets=20,
            replies=10,
        )
        article = post.to_news_article(symbols=["BTC-USD"])

        assert article.source == "grok"
        assert "BTC-USD" in article.symbols
        assert article.sentiment is not None
        assert -1 <= article.sentiment <= 1
        assert article.url == post.url

    def test_grok_post_sentiment_calculation(self):
        """Test sentiment calculation from engagement metrics."""
        # High likes ratio = positive sentiment
        post_positive = GrokPost(
            post_id="1",
            text="Test",
            url="https://x.com/status/1",
            created_at=datetime.now(timezone.utc),
            likes=100,
            retweets=10,
            replies=10,
        )
        article_positive = post_positive.to_news_article()
        # likes/(likes+retweets+replies) * 2 - 1 = 100/120 * 2 - 1 = 0.667
        assert article_positive.sentiment > 0.5

        # Lower likes ratio = less positive sentiment
        post_neutral = GrokPost(
            post_id="2",
            text="Test",
            url="https://x.com/status/2",
            created_at=datetime.now(timezone.utc),
            likes=50,
            retweets=50,
            replies=50,
        )
        article_neutral = post_neutral.to_news_article()
        # 50/150 * 2 - 1 = -0.333
        assert -0.5 < article_neutral.sentiment < 0

    def test_grok_post_zero_engagement(self):
        """Test sentiment with zero engagement."""
        post = GrokPost(
            post_id="3",
            text="Test",
            url="https://x.com/status/3",
            created_at=datetime.now(timezone.utc),
            likes=0,
            retweets=0,
            replies=0,
        )
        article = post.to_news_article()
        assert article.sentiment == 0.0


class TestGrokClient:
    """Test Grok API client."""

    @pytest.mark.asyncio
    async def test_get_news_success(self):
        """Test successful news fetching from Grok API."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GROK_API_RESPONSE
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                articles = await client.get_news(symbols=["BTC-USD"])

                assert len(articles) > 0
                assert articles[0].source == "grok"
                # Verify engagement filtering worked (both posts have 100+ likes)
                assert all(
                    "Engagement:" in article.summary for article in articles if article.summary
                )

    @pytest.mark.asyncio
    async def test_get_news_without_api_key(self):
        """Test that missing API key raises ValueError."""
        client = GrokClient(api_key="")
        with pytest.raises(ValueError, match="Grok API key is required"):
            await client.get_news()

    @pytest.mark.asyncio
    async def test_get_news_with_invalid_api_key(self):
        """Test handling of 401 Unauthorized error."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response
            )
            mock_post.return_value = mock_response

            async with GrokClient(api_key="invalid_key") as client:
                with pytest.raises(ValueError, match="Invalid Grok API key"):
                    await client.get_news()

    @pytest.mark.asyncio
    async def test_get_news_rate_limit(self):
        """Test handling of 429 Rate Limit error."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = __import__("httpx").HTTPStatusError(
                "Too Many Requests", request=Mock(), response=mock_response
            )
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                with pytest.raises(ConnectionError, match="rate limit"):
                    await client.get_news()

    @pytest.mark.asyncio
    async def test_engagement_filtering(self):
        """Test that posts with low engagement are filtered out."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GROK_API_RESPONSE_LOW_ENGAGEMENT
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key", min_engagement=100) as client:
                articles = await client.get_news(symbols=["BTC-USD"])

                # Should return empty list (post has only 5 likes, below 100 threshold)
                assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_retweet_exclusion(self):
        """Test that retweets are excluded."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GROK_API_RESPONSE_RETWEET
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                articles = await client.get_news(symbols=["BTC-USD"])

                # Should return empty list (post starts with "RT @")
                assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_time_window_filtering(self):
        """Test time window filtering."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GROK_API_RESPONSE
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                # Set time window that excludes the mock posts
                end_time = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
                start_time = end_time - timedelta(hours=1)

                articles = await client.get_news(
                    symbols=["BTC-USD"], start_time=start_time, end_time=end_time
                )

                # Should return empty list (posts are at 12:00, outside window)
                assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with valid API."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                is_healthy = await client.health_check()
                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with failed connection."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            async with GrokClient(api_key="test_key") as client:
                is_healthy = await client.health_check()
                assert is_healthy is False

    def test_source_name(self):
        """Test source name property."""
        client = GrokClient(api_key="test_key")
        assert client.source_name == "grok"

    def test_build_search_query_with_symbols(self):
        """Test search query construction with symbols."""
        client = GrokClient(api_key="test_key")
        query = client._build_search_query(["BTC-USD", "ETH-USD"])

        # Should include both symbol codes and names
        assert "Bitcoin" in query or "BTC" in query
        assert "Ethereum" in query or "ETH" in query
        # Should include event keywords
        assert "surge" in query or "crash" in query or "rally" in query

    def test_build_search_query_without_symbols(self):
        """Test search query construction without symbols."""
        client = GrokClient(api_key="test_key")
        query = client._build_search_query(None)

        # Should return generic crypto query
        assert "crypto" in query.lower()
        assert "surge" in query or "crash" in query

    @pytest.mark.asyncio
    async def test_usage_tracking(self):
        """Test that usage is tracked correctly."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = MOCK_GROK_API_RESPONSE
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                await client.get_news(symbols=["BTC-USD"])

                # Check usage stats
                stats = client.usage_stats
                assert stats["request_count"] == 1
                assert stats["cumulative_cost"] > 0
                assert stats["free_tier_limit"] == 25.0
                assert stats["usage_percentage"] < 100

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed API responses."""
        malformed_response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "x_search",
                                    "arguments": "invalid json",  # Malformed JSON
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = malformed_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                # Should handle gracefully and return empty list
                articles = await client.get_news(symbols=["BTC-USD"])
                assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_symbol_matching_verification(self):
        """Test that posts are verified to contain symbols."""
        with patch("httpx.AsyncClient.post") as mock_post:
            # Create response with post that doesn't mention the symbol
            no_symbol_response = {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "x_search",
                                        "arguments": json.dumps(
                                            {
                                                "results": [
                                                    {
                                                        "id": "999",
                                                        "text": "General crypto market discussion without specific coins",
                                                        "url": "https://x.com/status/999",
                                                        "created_at": "2024-01-15T12:00:00Z",
                                                        "likes": 200,
                                                        "retweets": 20,
                                                        "replies": 10,
                                                    }
                                                ]
                                            }
                                        ),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            }

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = no_symbol_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with GrokClient(api_key="test_key") as client:
                # Search for BTC-USD but post doesn't mention Bitcoin or BTC
                articles = await client.get_news(symbols=["BTC-USD"])

                # Should be filtered out due to missing symbol
                assert len(articles) == 0
