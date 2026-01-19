"""Example script to test news aggregation functionality.

This script demonstrates:
1. Individual news client usage (CryptoPanic, NewsAPI)
2. NewsAggregator for combined news fetching
3. Time-windowed news fetching for anomaly correlation
4. Health checks for all news sources

Usage:
    python examples/test_news_aggregation.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from src.phase1_detector.news_aggregation import (
    CryptoPanicClient,
    NewsAPIClient,
    NewsAggregator,
)
from config.settings import settings


async def test_individual_clients():
    """Test individual news clients."""
    print("=" * 80)
    print("TESTING INDIVIDUAL NEWS CLIENTS")
    print("=" * 80)

    # Test CryptoPanic
    print("\n1. Testing CryptoPanic Client")
    print("-" * 80)
    try:
        async with CryptoPanicClient(api_key=settings.news.cryptopanic_api_key) as client:
            # Health check
            is_healthy = await client.health_check()
            print(f"Health: {'✓ OK' if is_healthy else '✗ FAILED'}")

            if is_healthy:
                # Get recent BTC news
                articles = await client.get_news(symbols=["BTC-USD"], limit=5)
                print(f"Found {len(articles)} articles")

                for i, article in enumerate(articles[:3], 1):
                    print(f"\n  Article {i}:")
                    print(f"    Title: {article.title[:70]}...")
                    print(f"    Source: {article.source}")
                    print(f"    Published: {article.published_at}")
                    print(f"    Symbols: {', '.join(article.symbols)}")
                    if article.sentiment:
                        sentiment = "Bullish" if article.sentiment > 0 else "Bearish"
                        print(f"    Sentiment: {sentiment} ({article.sentiment:.2f})")
    except Exception as e:
        print(f"✗ CryptoPanic Error: {e}")

    # Test NewsAPI (optional)
    if settings.news.newsapi_api_key:
        print("\n2. Testing NewsAPI Client")
        print("-" * 80)
        try:
            client = NewsAPIClient(api_key=settings.news.newsapi_api_key)

            # Health check
            is_healthy = await client.health_check()
            print(f"Health: {'✓ OK' if is_healthy else '✗ FAILED'}")

            if is_healthy:
                # Get recent crypto news from last 24 hours
                start_time = datetime.now(timezone.utc) - timedelta(hours=24)
                articles = await client.get_news(
                    symbols=["BTC", "ETH"], start_time=start_time, limit=5
                )
                print(f"Found {len(articles)} articles")

                for i, article in enumerate(articles[:3], 1):
                    print(f"\n  Article {i}:")
                    print(f"    Title: {article.title[:70]}...")
                    print(f"    Source: {article.source}")
                    print(f"    Published: {article.published_at}")
        except Exception as e:
            print(f"✗ NewsAPI Error: {e}")
    else:
        print("\n3. Testing NewsAPI Client")
        print("-" * 80)
        print("Skipped (no API key configured)")


async def test_aggregator():
    """Test NewsAggregator for combined news fetching."""
    print("\n" + "=" * 80)
    print("TESTING NEWS AGGREGATOR")
    print("=" * 80)

    try:
        aggregator = NewsAggregator()
        print(f"\nInitialized: {aggregator}")

        # Health check
        print("\nHealth Check:")
        print("-" * 80)
        health = await aggregator.health_check()
        for source, status in health.items():
            print(f"  {source}: {'✓ OK' if status else '✗ FAILED'}")

        # Get recent news for BTC and ETH
        print("\nFetching Recent News (BTC, ETH):")
        print("-" * 80)
        articles = await aggregator.get_news(symbols=["BTC-USD", "ETH-USD"], limit_per_source=10)
        print(f"Total articles: {len(articles)}")

        # Group by source
        by_source = {}
        for article in articles:
            if article.source not in by_source:
                by_source[article.source] = []
            by_source[article.source].append(article)

        print("\nBreakdown by source:")
        for source, source_articles in by_source.items():
            print(f"  {source}: {len(source_articles)} articles")

        # Show sample articles
        print("\nSample Articles:")
        print("-" * 80)
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. [{article.source.upper()}] {article.title[:70]}...")
            print(f"   Published: {article.published_at}")
            print(f"   URL: {article.url}")
            if article.symbols:
                print(f"   Symbols: {', '.join(article.symbols)}")

    except Exception as e:
        print(f"✗ Aggregator Error: {e}")


async def test_anomaly_window():
    """Test time-windowed news fetching for anomaly correlation."""
    print("\n" + "=" * 80)
    print("TESTING ANOMALY TIME WINDOW")
    print("=" * 80)

    try:
        aggregator = NewsAggregator()

        # Simulate an anomaly detected 10 minutes ago
        anomaly_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        print(f"\nSimulated Anomaly:")
        print(f"  Symbol: BTC-USD")
        print(f"  Detected At: {anomaly_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Time Window: ±30 minutes")

        # Get news within time window
        print("\nFetching News Within Time Window:")
        print("-" * 80)
        articles = await aggregator.get_news_for_anomaly(
            symbols=["BTC-USD"],
            anomaly_time=anomaly_time,
            window_minutes=30,
            limit_per_source=20,
        )

        print(f"Total articles: {len(articles)}")

        # Analyze timing
        pre_event = [a for a in articles if hasattr(a, "timing_tag") and a.timing_tag == "pre_event"]
        post_event = [
            a for a in articles if hasattr(a, "timing_tag") and a.timing_tag == "post_event"
        ]

        print(f"\nTiming Analysis:")
        print(f"  Pre-event (before anomaly): {len(pre_event)}")
        print(f"  Post-event (after anomaly): {len(post_event)}")

        # Show articles with timing
        print("\nArticles with Timing Tags:")
        print("-" * 80)
        for i, article in enumerate(articles[:5], 1):
            timing = getattr(article, "timing_tag", "unknown")
            time_diff = getattr(article, "time_diff_minutes", 0)
            timing_str = f"{time_diff:+.0f} min" if time_diff else "N/A"

            print(f"\n{i}. [{article.source.upper()}] {article.title[:60]}...")
            print(f"   Published: {article.published_at.strftime('%H:%M:%S UTC')}")
            print(f"   Timing: {timing} ({timing_str})")

    except Exception as e:
        print(f"✗ Time Window Error: {e}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("NEWS AGGREGATION TEST SUITE")
    print("=" * 80)
    print("\nThis script tests the Phase 1 news aggregation functionality.")
    print("Make sure you have configured API keys in your .env file:")
    print("  - NEWS__CRYPTOPANIC_API_KEY")
    print("  - NEWS__NEWSAPI_API_KEY (optional)")

    # Run tests
    await test_individual_clients()
    await test_aggregator()
    await test_anomaly_window()

    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
