# Historical News Datasets for Replay Mode

This directory contains historical news datasets used in **replay mode** for deterministic testing and demos.

## Purpose

- **Deterministic Testing**: Replay produces identical results across runs
- **Cost-Free Demos**: No API calls required
- **Known Event Validation**: Test against major crypto events

## File Naming Convention

```
{SYMBOL}_{DATE}.json
```

Examples:
- `BTC-USD_2024-03-14.json` - Bitcoin ETF approval day
- `ETH-USD_2023-09-15.json` - Ethereum Merge event

## JSON Schema

Each dataset file must follow this structure:

```json
{
  "symbol": "BTC-USD",
  "date": "2024-03-14",
  "articles": [
    {
      "source": "coindesk",
      "title": "Bitcoin Surges Past $73,000 on ETF Inflows",
      "url": "https://www.coindesk.com/...",
      "published_at": "2024-03-14T14:30:00Z",
      "summary": "Bitcoin reached a new all-time high...",
      "sentiment": 0.85,
      "symbols": ["BTC-USD"]
    },
    {
      "source": "cointelegraph",
      "title": "Institutional Demand Drives BTC Rally",
      "url": "https://cointelegraph.com/...",
      "published_at": "2024-03-14T15:00:00Z",
      "summary": "Record ETF inflows fuel Bitcoin momentum...",
      "sentiment": 0.75,
      "symbols": ["BTC-USD"]
    }
  ]
}
```

## Required Fields

Each article must have:
- `source`: News source identifier (string)
- `title`: Article headline (string)
- `url`: Article URL (string, optional)
- `published_at`: ISO 8601 timestamp with timezone (string)
- `sentiment`: Sentiment score -1.0 to 1.0 (float, optional)
- `summary`: Article summary (string, optional)
- `symbols`: List of crypto symbols (array, optional but recommended)

## Creating Datasets

### Method 1: Manual Creation

Create JSON files manually using the schema above.

### Method 2: Using backfill-news Command

```bash
# Prepare source data in JSON format
cat > news_source.json <<EOF
{
  "articles": [
    {
      "title": "Bitcoin Surges",
      "url": "https://example.com/article",
      "published_at": "2024-03-14T14:30:00Z",
      "source": "coindesk",
      "summary": "Bitcoin reached new highs...",
      "sentiment": 0.8
    }
  ]
}
EOF

# Convert to replay dataset
mane backfill-news \
  --symbol BTC-USD \
  --start-date 2024-03-14 \
  --end-date 2024-03-14 \
  --file-path news_source.json
```

## Using Replay Mode

### Single Detection

```bash
mane detect --symbol BTC-USD --news-mode replay
```

### Continuous Monitoring

```bash
mane serve --news-mode replay
```

### Hybrid Mode (Live + Replay)

```bash
mane detect --symbol BTC-USD --news-mode hybrid
```

## Data Sources

Historical news data can be collected from:
- Kaggle crypto news datasets
- Archive.org cached news pages
- Personal news scraping (respect robots.txt)
- Manual curation of known events

## Example Datasets

See sample datasets in this directory:
- `BTC-USD_sample.json` - Sample dataset with 10 articles

## Notes

- Timestamps must be timezone-aware (use UTC with 'Z' suffix or '+00:00')
- Sentiment scores are optional; system will use 0.0 (neutral) if missing
- Articles are filtered by time window (±30 minutes around anomaly)
- Replay mode requires explicit symbols (no wildcard matching)
