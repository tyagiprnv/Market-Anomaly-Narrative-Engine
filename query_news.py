"""Standalone script to query news articles from the database."""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, selectinload

from config.settings import Settings
from src.database.models import NewsArticle, Anomaly


def query_all_news(session, limit=20):
    """Query all news articles."""
    articles = (
        session.query(NewsArticle)
        .join(Anomaly)
        .options(selectinload(NewsArticle.anomaly))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
        .all()
    )

    print(f"\n{'='*80}")
    print(f"ALL NEWS ARTICLES (Last {len(articles)})")
    print(f"{'='*80}\n")

    for article in articles:
        print(f"Symbol: {article.anomaly.symbol}")
        print(f"Source: {article.source}")
        print(f"Published: {article.published_at}")
        print(f"Title: {article.title}")
        print(f"Sentiment: {article.sentiment if article.sentiment else 'N/A'}")
        print(f"Timing: {article.timing_tag} ({article.time_diff_minutes:.1f} min)")
        print(f"URL: {article.url}")
        print(f"Summary: {article.summary[:100]}..." if article.summary else "No summary")
        print("-" * 80)


def query_news_by_symbol(session, symbol, limit=10):
    """Query news articles for a specific symbol."""
    articles = (
        session.query(NewsArticle)
        .join(Anomaly)
        .filter(Anomaly.symbol == symbol)
        .options(selectinload(NewsArticle.anomaly))
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
        .all()
    )

    print(f"\n{'='*80}")
    print(f"NEWS ARTICLES FOR {symbol} (Last {len(articles)})")
    print(f"{'='*80}\n")

    for article in articles:
        print(f"Published: {article.published_at}")
        print(f"Source: {article.source}")
        print(f"Title: {article.title}")
        print(f"Sentiment: {article.sentiment if article.sentiment else 'N/A'}")
        print(f"Anomaly Type: {article.anomaly.anomaly_type.value}")
        print(f"Anomaly Time: {article.anomaly.detected_at}")
        print("-" * 80)


def query_news_by_anomaly(session, anomaly_id):
    """Query news articles for a specific anomaly."""
    articles = (
        session.query(NewsArticle)
        .filter(NewsArticle.anomaly_id == anomaly_id)
        .options(selectinload(NewsArticle.anomaly))
        .order_by(NewsArticle.published_at)
        .all()
    )

    if not articles:
        print(f"\nNo news articles found for anomaly {anomaly_id}")
        return

    anomaly = articles[0].anomaly
    print(f"\n{'='*80}")
    print(f"NEWS ARTICLES FOR ANOMALY {anomaly_id}")
    print(f"Symbol: {anomaly.symbol} | Type: {anomaly.anomaly_type.value}")
    print(f"Detected: {anomaly.detected_at} | Change: {anomaly.price_change_pct:+.2f}%")
    print(f"{'='*80}\n")

    for article in articles:
        print(f"[{article.timing_tag}] {article.published_at.strftime('%H:%M:%S')}")
        print(f"  Source: {article.source}")
        print(f"  Title: {article.title}")
        print(f"  Sentiment: {article.sentiment if article.sentiment else 'N/A'}")
        print(f"  Cluster: {article.cluster_id}")
        print("-" * 80)


def query_news_stats(session):
    """Get statistics about news articles."""
    total_articles = session.query(func.count(NewsArticle.id)).scalar()

    # Count by source
    sources = (
        session.query(NewsArticle.source, func.count(NewsArticle.id))
        .group_by(NewsArticle.source)
        .all()
    )

    # Count by symbol
    symbols = (
        session.query(Anomaly.symbol, func.count(NewsArticle.id))
        .join(NewsArticle)
        .group_by(Anomaly.symbol)
        .all()
    )

    # Average sentiment by symbol
    avg_sentiments = (
        session.query(
            Anomaly.symbol,
            func.avg(NewsArticle.sentiment),
            func.count(NewsArticle.id)
        )
        .join(NewsArticle)
        .filter(NewsArticle.sentiment.isnot(None))
        .group_by(Anomaly.symbol)
        .all()
    )

    print(f"\n{'='*80}")
    print("NEWS ARTICLE STATISTICS")
    print(f"{'='*80}\n")

    print(f"Total Articles: {total_articles}\n")

    print("Articles by Source:")
    for source, count in sources:
        print(f"  {source}: {count}")

    print("\nArticles by Symbol:")
    for symbol, count in symbols:
        print(f"  {symbol}: {count}")

    print("\nAverage Sentiment by Symbol:")
    for symbol, avg_sent, count in avg_sentiments:
        print(f"  {symbol}: {avg_sent:.3f} ({count} articles)")


def query_recent_anomalies_with_news(session, limit=5):
    """Query recent anomalies with their associated news count."""
    anomalies = (
        session.query(Anomaly)
        .options(selectinload(Anomaly.news_articles))
        .order_by(Anomaly.detected_at.desc())
        .limit(limit)
        .all()
    )

    print(f"\n{'='*80}")
    print(f"RECENT ANOMALIES WITH NEWS COUNTS")
    print(f"{'='*80}\n")

    for anomaly in anomalies:
        news_count = len(anomaly.news_articles)
        print(f"Symbol: {anomaly.symbol}")
        print(f"Detected: {anomaly.detected_at}")
        print(f"Type: {anomaly.anomaly_type.value}")
        print(f"Change: {anomaly.price_change_pct:+.2f}%")
        print(f"News Articles: {news_count}")

        if news_count > 0:
            sources = {}
            for article in anomaly.news_articles:
                sources[article.source] = sources.get(article.source, 0) + 1
            print(f"Sources: {', '.join(f'{k}({v})' for k, v in sources.items())}")

        print("-" * 80)


def main():
    """Main function to run queries."""
    # Load settings
    settings = Settings()

    # Create database connection
    engine = create_engine(settings.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n" + "="*80)
        print("MARKET ANOMALY NARRATIVE ENGINE - NEWS QUERY TOOL")
        print("="*80)

        # Run various queries
        query_news_stats(session)
        query_recent_anomalies_with_news(session, limit=5)
        query_all_news(session, limit=10)

        # Example: Query specific symbol (uncomment and change symbol as needed)
        # query_news_by_symbol(session, "BTC-USD", limit=10)

        # Example: Query specific anomaly (uncomment and add anomaly_id)
        # query_news_by_anomaly(session, "your-anomaly-id-here")

    finally:
        session.close()


if __name__ == "__main__":
    main()
