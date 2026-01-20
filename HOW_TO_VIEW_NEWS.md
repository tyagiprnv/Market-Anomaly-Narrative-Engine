# How to View Stored News Articles

This guide explains all the ways to query and view news articles that are stored when running `mane serve` or `mane detect`.

## Quick Answer

**Yes, news articles ARE stored in the database!** They're saved in the `news_articles` table whenever an anomaly is detected.

## Methods to View News Articles

### Method 1: CLI Command (Easiest)

The new `mane list-news` command provides an easy way to view news articles:

```bash
# View last 20 news articles
mane list-news

# View news for specific symbol
mane list-news --symbol BTC-USD

# View news from specific source
mane list-news --source rss

# View news for specific anomaly
mane list-news --anomaly-id <anomaly-id>

# Limit number of results
mane list-news --limit 50

# Get JSON output for programmatic use
mane list-news --format json --symbol BTC-USD > btc_news.json
```

**Example Output:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                        News Articles (15)                           │
├────────┬────────────┬───────────┬─────────────────────┬──────┬──────┤
│ Symbol │ Published  │ Source    │ Title               │ Sent │ Time │
├────────┼────────────┼───────────┼─────────────────────┼──────┼──────┤
│BTC-USD │ 01-20 14:30│ rss       │ Bitcoin Surges Past │+0.85 │Pre..│
│        │            │           │ $50K                │      │      │
├────────┼────────────┼───────────┼─────────────────────┼──────┼──────┤
│BTC-USD │ 01-20 14:35│ coindesk  │ Market Analysis:    │+0.45 │Post.│
│        │            │           │ BTC Rally Continues │      │      │
└────────┴────────────┴───────────┴─────────────────────┴──────┴──────┘

Sources: rss(8), coindesk(4), cointelegraph(3)
Average Sentiment: +0.52
```

### Method 2: Python Query Script

Run the standalone Python script to get detailed information:

```bash
python query_news.py
```

This script provides:
- Overall statistics (total articles, articles by source/symbol)
- Recent anomalies with news counts
- Last 10 news articles with full details
- Average sentiment by symbol

You can also import and use the query functions in your own scripts:

```python
from query_news import query_news_by_symbol, query_news_stats
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import Settings

settings = Settings()
engine = create_engine(settings.database.url)
Session = sessionmaker(bind=engine)
session = Session()

# Get news for BTC
query_news_by_symbol(session, "BTC-USD", limit=10)

# Get statistics
query_news_stats(session)

session.close()
```

### Method 3: Direct SQL Queries

Connect to PostgreSQL and run queries directly:

```bash
# Connect to database
psql -h localhost -U postgres -d mane
```

**Example Queries:**

```sql
-- View all news articles
SELECT
    a.symbol,
    na.source,
    na.published_at,
    na.title,
    na.sentiment,
    na.timing_tag
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
ORDER BY na.published_at DESC
LIMIT 20;

-- Count articles by source
SELECT source, COUNT(*) as count
FROM news_articles
GROUP BY source;

-- Get articles for specific symbol
SELECT * FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
WHERE a.symbol = 'BTC-USD'
ORDER BY na.published_at DESC;
```

See `NEWS_QUERIES.md` for a complete reference of SQL queries.

### Method 4: Database GUI (pgAdmin, DBeaver, etc.)

1. Open your database client
2. Connect to:
   - Host: `localhost`
   - Port: `5432`
   - Database: `mane`
   - Username: `postgres`
   - Password: (from your `.env` file's `DATABASE__PASSWORD`)

3. Browse the `news_articles` table or run custom queries

## Understanding News Storage

### When Are News Articles Stored?

News articles are stored **only when an anomaly is detected**:

1. `mane serve` runs continuously
2. Every poll interval (default: 60s), it checks for anomalies
3. **If an anomaly is detected:**
   - News is fetched within ±30 minutes of the anomaly time
   - Articles are stored in the `news_articles` table
   - Articles are linked to the anomaly via `anomaly_id`
   - Articles are clustered using embeddings
4. If no anomaly, no news is fetched/stored

### News Article Schema

Each stored news article contains:

```
NewsArticle
├── id                    - Unique identifier
├── anomaly_id           - Links to the anomaly
├── source               - rss, cryptopanic, newsapi, grok
├── title                - Article headline
├── url                  - Article URL
├── published_at         - When article was published
├── summary              - Article summary/content
├── sentiment            - Sentiment score (-1 to 1)
├── symbols              - Related crypto symbols (JSON array)
├── timing_tag           - pre_event or post_event
├── time_diff_minutes    - Minutes before/after anomaly
├── cluster_id           - News cluster assignment
├── embedding            - Vector embedding (JSON array)
└── created_at           - When stored in database
```

### News Sources

Depending on your `NEWS__MODE` setting:

- **live mode**: RSS feeds (CoinDesk, Cointelegraph, Decrypt, etc.)
- **replay mode**: Historical datasets from `datasets/news/*.json`
- **hybrid mode**: Both live and replay sources

All news, regardless of source, is stored in the same table.

## Common Queries

### "How many news articles do I have?"

```bash
mane list-news --limit 1000 --format json | jq length
```

Or in SQL:
```sql
SELECT COUNT(*) FROM news_articles;
```

### "Which anomaly has the most news coverage?"

```sql
SELECT
    a.symbol,
    a.detected_at,
    a.anomaly_type,
    COUNT(na.id) as news_count
FROM anomalies a
LEFT JOIN news_articles na ON a.id = na.anomaly_id
GROUP BY a.id, a.symbol, a.detected_at, a.anomaly_type
ORDER BY news_count DESC
LIMIT 10;
```

### "What's the sentiment around recent BTC anomalies?"

```bash
mane list-news --symbol BTC-USD --format json | jq '[.[] | .sentiment] | add / length'
```

### "Show me all pre-event news (early warnings)"

```sql
SELECT
    a.symbol,
    na.published_at,
    na.title,
    na.sentiment,
    na.time_diff_minutes
FROM news_articles na
JOIN anomalies a ON na.anomaly_id = a.id
WHERE na.timing_tag = 'pre_event'
ORDER BY ABS(na.time_diff_minutes)
LIMIT 20;
```

### "Which news sources are most active?"

```bash
mane list-news --limit 1000 --format json | jq 'group_by(.source) | map({source: .[0].source, count: length}) | sort_by(.count) | reverse'
```

## Verifying News Storage

After running `mane serve` for a while, verify news is being stored:

```bash
# Check if any news articles exist
psql -h localhost -U postgres -d mane -c "SELECT COUNT(*) FROM news_articles;"

# Or use the CLI
mane list-news --limit 5
```

If you see news articles, the system is working correctly!

## Troubleshooting

### "I don't see any news articles"

1. **Check if anomalies were detected:**
   ```bash
   mane list-narratives
   ```
   If no narratives exist, no anomalies were detected, so no news was fetched.

2. **Check your news mode:**
   - In `replay` mode, you need historical datasets in `datasets/news/`
   - In `live` mode, news is fetched from RSS feeds (may take time)

3. **Verify database connection:**
   ```bash
   mane list-news
   ```
   If this fails, check your `.env` file's `DATABASE__PASSWORD`

### "News articles exist but have NULL sentiment"

This may happen with older data. The sentiment field was recently added. New articles will have sentiment scores.

### "I want to export all news to CSV"

```bash
# Using CLI + jq + JSON2CSV
mane list-news --limit 10000 --format json | jq -r '(.[0] | keys_unsorted) as $keys | $keys, map([.[ $keys[] ]])[] | @csv' > news.csv

# Or use PostgreSQL COPY
psql -h localhost -U postgres -d mane -c "COPY (SELECT * FROM news_articles) TO STDOUT WITH CSV HEADER" > news.csv
```

## Additional Resources

- `NEWS_QUERIES.md` - Complete SQL query reference
- `query_news.py` - Python script for custom queries
- `CLAUDE.md` - Full project documentation

## Summary

**To view stored news articles, simply run:**

```bash
mane list-news
```

All news articles linked to detected anomalies are stored in the `news_articles` table and can be queried using the CLI, Python scripts, or direct SQL queries.
