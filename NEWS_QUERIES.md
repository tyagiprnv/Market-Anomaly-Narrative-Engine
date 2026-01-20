# News Article Query Reference

This document provides SQL queries and Python examples to query stored news articles.

## Database Schema

The `news_articles` table has the following structure:

```sql
news_articles
├── id (UUID)
├── anomaly_id (FK to anomalies)
├── source (string) - cryptopanic, newsapi, rss, grok
├── title (text)
├── url (text)
├── published_at (datetime)
├── summary (text)
├── sentiment (float) - sentiment score (-1 to 1)
├── symbols (JSON array) - related trading symbols
├── cluster_id (int) - cluster assignment (-1 for unclustered)
├── embedding (JSON array) - article embedding vector
├── timing_tag (string) - pre_event or post_event
├── time_diff_minutes (float) - minutes before/after anomaly
└── created_at (datetime)
```

## SQL Queries

### 1. View All News Articles

```sql
SELECT
    a.symbol,
    na.source,
    na.published_at,
    na.title,
    na.sentiment,
    na.timing_tag,
    na.time_diff_minutes,
    a.detected_at as anomaly_time
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
ORDER BY na.published_at DESC
LIMIT 20;
```

### 2. Count News Articles by Source

```sql
SELECT
    source,
    COUNT(*) as article_count
FROM news_articles
GROUP BY source
ORDER BY article_count DESC;
```

### 3. News Articles for Specific Symbol

```sql
SELECT
    na.published_at,
    na.source,
    na.title,
    na.sentiment,
    na.url,
    a.anomaly_type,
    a.price_change_pct
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
WHERE a.symbol = 'BTC-USD'
ORDER BY na.published_at DESC
LIMIT 10;
```

### 4. News Articles for Specific Anomaly

```sql
SELECT
    published_at,
    source,
    title,
    sentiment,
    timing_tag,
    time_diff_minutes,
    cluster_id
FROM news_articles
WHERE anomaly_id = 'your-anomaly-id-here'
ORDER BY published_at;
```

### 5. Average Sentiment by Symbol

```sql
SELECT
    a.symbol,
    AVG(na.sentiment) as avg_sentiment,
    COUNT(na.id) as article_count,
    MIN(na.published_at) as first_article,
    MAX(na.published_at) as last_article
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
WHERE na.sentiment IS NOT NULL
GROUP BY a.symbol
ORDER BY avg_sentiment DESC;
```

### 6. Recent Anomalies with News Counts

```sql
SELECT
    a.symbol,
    a.detected_at,
    a.anomaly_type,
    a.price_change_pct,
    COUNT(na.id) as news_count
FROM anomalies a
LEFT JOIN news_articles na ON a.id = na.anomaly_id
GROUP BY a.id, a.symbol, a.detected_at, a.anomaly_type, a.price_change_pct
ORDER BY a.detected_at DESC
LIMIT 10;
```

### 7. Pre-Event vs Post-Event News

```sql
SELECT
    timing_tag,
    COUNT(*) as count,
    AVG(sentiment) as avg_sentiment
FROM news_articles
WHERE timing_tag IS NOT NULL
GROUP BY timing_tag;
```

### 8. News Articles by Cluster

```sql
SELECT
    cluster_id,
    COUNT(*) as articles_in_cluster,
    AVG(sentiment) as avg_sentiment,
    STRING_AGG(DISTINCT source, ', ') as sources
FROM news_articles
WHERE cluster_id != -1
GROUP BY cluster_id
ORDER BY articles_in_cluster DESC;
```

### 9. Most Active News Sources (Last 7 Days)

```sql
SELECT
    source,
    COUNT(*) as article_count,
    AVG(sentiment) as avg_sentiment
FROM news_articles
WHERE published_at >= NOW() - INTERVAL '7 days'
GROUP BY source
ORDER BY article_count DESC;
```

### 10. News Articles with High Absolute Sentiment

```sql
SELECT
    a.symbol,
    na.published_at,
    na.source,
    na.title,
    na.sentiment,
    a.price_change_pct
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
WHERE ABS(na.sentiment) > 0.7
ORDER BY ABS(na.sentiment) DESC
LIMIT 20;
```

### 11. Detailed Anomaly Report with News

```sql
SELECT
    a.id as anomaly_id,
    a.symbol,
    a.detected_at,
    a.anomaly_type,
    a.price_change_pct,
    a.confidence,
    na.source,
    na.published_at,
    na.title,
    na.sentiment,
    na.timing_tag,
    na.cluster_id
FROM anomalies a
LEFT JOIN news_articles na ON a.id = na.anomaly_id
WHERE a.symbol = 'BTC-USD'
ORDER BY a.detected_at DESC, na.published_at;
```

## CLI Commands

### View News Articles

```bash
# View last 20 news articles
mane list-news

# View news for specific symbol
mane list-news --symbol BTC-USD

# View news from specific source
mane list-news --source rss

# View news for specific anomaly
mane list-news --anomaly-id <anomaly-id>

# Limit results
mane list-news --limit 50

# Output as JSON
mane list-news --format json
```

### View Narratives (includes associated news counts)

```bash
# View last 10 narratives
mane list-narratives

# View narratives for specific symbol
mane list-narratives --symbol BTC-USD

# View only validated narratives
mane list-narratives --validated-only
```

## Python Query Examples

### Using the Query Script

```bash
# Run the standalone query script
python query_news.py
```

### Custom Python Queries

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from config.settings import Settings
from src.database.models import NewsArticle, Anomaly

# Setup
settings = Settings()
engine = create_engine(settings.database.url)
Session = sessionmaker(bind=engine)
session = Session()

# Query all news for a symbol
articles = (
    session.query(NewsArticle)
    .join(Anomaly)
    .filter(Anomaly.symbol == "BTC-USD")
    .options(selectinload(NewsArticle.anomaly))
    .order_by(NewsArticle.published_at.desc())
    .limit(10)
    .all()
)

for article in articles:
    print(f"{article.published_at}: {article.title}")
    print(f"  Sentiment: {article.sentiment}")
    print(f"  Source: {article.source}")

session.close()
```

## Accessing the Database Directly

### Using psql

```bash
# Connect to database
psql -h localhost -U postgres -d mane

# Run queries
SELECT COUNT(*) FROM news_articles;
SELECT DISTINCT source FROM news_articles;
```

### Using pgAdmin or DBeaver

1. Create a new connection:
   - Host: localhost
   - Port: 5432
   - Database: mane
   - Username: postgres
   - Password: (from your .env DATABASE__PASSWORD)

2. Run any of the SQL queries above in the query editor

## News Article Fields Explained

- **source**: Where the article came from (rss, cryptopanic, newsapi, grok)
- **sentiment**: Keyword-based sentiment score from -1 (bearish) to +1 (bullish)
- **timing_tag**: Whether article was published before (`pre_event`) or after (`post_event`) the anomaly
- **time_diff_minutes**: How many minutes before/after the anomaly the article was published
- **cluster_id**: Which news cluster this article belongs to (-1 for noise/unclustered)
- **symbols**: JSON array of related cryptocurrency symbols

## Common Use Cases

1. **Investigate a specific anomaly**: Use query #4 to see all news associated with an anomaly
2. **Compare news sources**: Use query #2 to see which sources provide most articles
3. **Sentiment analysis**: Use query #5 to see overall sentiment by symbol
4. **Timing analysis**: Use query #7 to compare pre-event vs post-event news
5. **Quality check**: Use queries #6 and #11 to verify anomalies have associated news
