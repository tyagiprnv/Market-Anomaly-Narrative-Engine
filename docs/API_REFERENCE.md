# REST API Reference

## Overview

The Market Anomaly Narrative Engine provides a **production-ready REST API** for accessing anomaly data, narratives, news articles, price history, and system configuration.

**Base URL**: `http://localhost:3001` (development) or `https://api.yourdomain.com` (production)

**Authentication**: JWT tokens via httpOnly cookies

**Rate Limits**:
- Authentication endpoints: 5 requests / 15 minutes
- API endpoints: 100 requests / minute

## Authentication

### Register User

Create a new user account.

**Endpoint**: `POST /auth/register`

**Request Body**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "message": "Registration successful",
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2024-01-15T14:30:00Z"
  }
}
```

**Error Responses**:
- `400 Bad Request` - Invalid input (missing fields, weak password)
- `409 Conflict` - Email already exists

---

### Login

Authenticate and receive JWT token.

**Endpoint**: `POST /auth/login`

**Request Body**:
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Sets Cookie**:
```
Set-Cookie: auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; HttpOnly; Secure; SameSite=Lax; Max-Age=604800
```

**Error Responses**:
- `401 Unauthorized` - Invalid credentials
- `429 Too Many Requests` - Rate limit exceeded

---

### Logout

Clear authentication token.

**Endpoint**: `POST /auth/logout`

**Headers**:
```
Cookie: auth_token=...
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

**Clears Cookie**: Removes `auth_token` cookie

---

### Get Current User

Retrieve authenticated user information.

**Endpoint**: `GET /auth/me`

**Headers**:
```
Cookie: auth_token=...
```

**Response** (200 OK):
```json
{
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2024-01-15T14:30:00Z"
  }
}
```

**Error Responses**:
- `401 Unauthorized` - Not authenticated or invalid token

---

## Anomalies

### List Anomalies

Retrieve anomalies with filtering, pagination, and sorting.

**Endpoint**: `GET /api/anomalies`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Number of results (max 100) |
| `offset` | integer | 0 | Pagination offset |
| `symbol` | string | - | Filter by symbol (e.g., "BTC-USD") |
| `validated` | boolean | - | Filter by validation status |
| `anomaly_type` | string | - | Filter by type: `price_spike`, `price_drop`, `volume_spike`, `combined` |
| `start_date` | ISO 8601 | - | Start date for time range |
| `end_date` | ISO 8601 | - | End date for time range |
| `min_confidence` | float | - | Minimum confidence score (0-1) |
| `sort_by` | string | detected_at | Sort field: `detected_at`, `confidence`, `price_change_pct` |
| `sort_order` | string | desc | Sort order: `asc`, `desc` |

**Example Request**:
```bash
GET /api/anomalies?symbol=BTC-USD&validated=true&limit=10&offset=0
```

**Response** (200 OK):
```json
{
  "anomalies": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "symbol": "BTC-USD",
      "detected_at": "2024-01-15T14:15:32.123Z",
      "anomaly_type": "price_drop",
      "z_score": -3.87,
      "price_change_pct": -5.23,
      "volume_change_pct": 145.67,
      "confidence": 0.89,
      "baseline_window_minutes": 60,
      "price_before": 45000.50,
      "price_at_detection": 42651.00,
      "volume_before": 1234567890,
      "volume_at_detection": 3032456789,
      "detection_metadata": {
        "timeframe_minutes": 60,
        "volatility_tier": "stable",
        "asset_threshold": 3.5,
        "threshold_source": "asset_override",
        "detector": "MultiTimeframeDetector"
      },
      "created_at": "2024-01-15T14:15:32.123Z",
      "narrative": {
        "id": "uuid",
        "narrative_text": "Bitcoin dropped 5.2% at 2:15 PM UTC following SEC announcement of stricter cryptocurrency regulations. The negative sentiment across social media amplified the sell-off.",
        "confidence_score": 0.85,
        "validation_passed": true,
        "validation_score": 0.78,
        "validation_reason": null,
        "tools_used": ["verify_timestamp", "sentiment_check", "check_social_sentiment"],
        "llm_provider": "anthropic",
        "llm_model": "claude-3-5-haiku-20241022",
        "generation_time_seconds": 3.45,
        "created_at": "2024-01-15T14:15:36.789Z",
        "validated_at": "2024-01-15T14:15:38.123Z"
      }
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

**Error Responses**:
- `401 Unauthorized` - Not authenticated
- `400 Bad Request` - Invalid query parameters

---

### Get Anomaly Details

Retrieve detailed information about a specific anomaly including related news and price data.

**Endpoint**: `GET /api/anomalies/:id`

**Authentication**: Required

**Path Parameters**:
- `id` (string, required) - Anomaly UUID

**Example Request**:
```bash
GET /api/anomalies/550e8400-e29b-41d4-a716-446655440000
```

**Response** (200 OK):
```json
{
  "anomaly": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "BTC-USD",
    "detected_at": "2024-01-15T14:15:32.123Z",
    "anomaly_type": "price_drop",
    "z_score": -3.87,
    "price_change_pct": -5.23,
    "confidence": 0.89,
    "detection_metadata": {
      "timeframe_minutes": 60,
      "volatility_tier": "stable",
      "asset_threshold": 3.5
    },
    "narrative": {
      "narrative_text": "Bitcoin dropped 5.2%...",
      "validation_passed": true,
      "tools_used": ["verify_timestamp", "sentiment_check"]
    }
  },
  "news_articles": [
    {
      "id": "uuid",
      "title": "SEC Announces Stricter Crypto Regulations",
      "source": "CoinDesk",
      "url": "https://coindesk.com/article/...",
      "published_at": "2024-01-15T14:05:00Z",
      "summary": "The Securities and Exchange Commission announced...",
      "sentiment": "negative",
      "timing_tag": "pre_event",
      "time_diff_minutes": -10.5,
      "cluster_id": 1
    },
    {
      "id": "uuid",
      "title": "Bitcoin Tumbles Following Regulatory News",
      "source": "Cointelegraph",
      "url": "https://cointelegraph.com/news/...",
      "published_at": "2024-01-15T14:20:00Z",
      "summary": "Bitcoin experienced significant selling pressure...",
      "sentiment": "negative",
      "timing_tag": "post_event",
      "time_diff_minutes": 4.5,
      "cluster_id": 1
    }
  ],
  "news_clusters": [
    {
      "id": "uuid",
      "cluster_number": 1,
      "size": 5,
      "centroid_summary": "SEC Announces Stricter Crypto Regulations",
      "dominant_sentiment": "negative",
      "article_ids": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"]
    }
  ],
  "price_context": {
    "hour_before": 45123.50,
    "hour_after": 42891.25,
    "day_high": 46500.00,
    "day_low": 42500.00
  }
}
```

**Error Responses**:
- `401 Unauthorized` - Not authenticated
- `404 Not Found` - Anomaly not found

---

## News Articles

### List News Articles

Retrieve news articles with filtering.

**Endpoint**: `GET /api/news`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Number of results (max 200) |
| `offset` | integer | 0 | Pagination offset |
| `anomaly_id` | string | - | Filter by anomaly UUID |
| `symbol` | string | - | Filter by symbol |
| `source` | string | - | Filter by source (e.g., "CoinDesk") |
| `sentiment` | string | - | Filter by sentiment: `positive`, `negative`, `neutral` |
| `timing_tag` | string | - | Filter by timing: `pre_event`, `post_event` |
| `cluster_id` | integer | - | Filter by cluster (use -1 for unclustered) |

**Example Request**:
```bash
GET /api/news?anomaly_id=550e8400-e29b-41d4-a716-446655440000&limit=20
```

**Response** (200 OK):
```json
{
  "articles": [
    {
      "id": "uuid",
      "anomaly_id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "CoinDesk",
      "title": "SEC Announces Stricter Crypto Regulations",
      "url": "https://coindesk.com/article/...",
      "published_at": "2024-01-15T14:05:00Z",
      "summary": "The Securities and Exchange Commission...",
      "sentiment": "negative",
      "symbols": ["BTC-USD", "ETH-USD"],
      "timing_tag": "pre_event",
      "time_diff_minutes": -10.5,
      "cluster_id": 1,
      "created_at": "2024-01-15T14:15:33.456Z"
    }
  ],
  "pagination": {
    "total": 12,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

**Error Responses**:
- `401 Unauthorized` - Not authenticated
- `400 Bad Request` - Invalid query parameters

---

## Price Data

### Get Price History

Retrieve historical price data for charting.

**Endpoint**: `GET /api/prices`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Symbol (e.g., "BTC-USD") |
| `start_date` | ISO 8601 | Yes | Start timestamp |
| `end_date` | ISO 8601 | Yes | End timestamp |
| `interval` | string | No | Aggregation interval: `1m`, `5m`, `15m`, `1h`, `1d` (default: `1m`) |

**Example Request**:
```bash
GET /api/prices?symbol=BTC-USD&start_date=2024-01-15T13:00:00Z&end_date=2024-01-15T15:00:00Z&interval=1m
```

**Response** (200 OK):
```json
{
  "symbol": "BTC-USD",
  "interval": "1m",
  "prices": [
    {
      "timestamp": "2024-01-15T13:00:00Z",
      "price": 45123.50,
      "volume_24h": 28500000000,
      "high_24h": 46200.00,
      "low_24h": 44800.00,
      "bid": 45120.00,
      "ask": 45125.00,
      "source": "coinbase"
    },
    {
      "timestamp": "2024-01-15T13:01:00Z",
      "price": 45135.25,
      "volume_24h": 28520000000,
      "high_24h": 46200.00,
      "low_24h": 44800.00,
      "bid": 45132.00,
      "ask": 45137.00,
      "source": "coinbase"
    }
  ],
  "count": 120
}
```

**Error Responses**:
- `401 Unauthorized` - Not authenticated
- `400 Bad Request` - Missing required parameters or invalid date range
- `404 Not Found` - No price data for specified range

---

### Get Latest Price

Get the most recent price for a symbol.

**Endpoint**: `GET /api/prices/latest`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Symbol (e.g., "BTC-USD") |

**Example Request**:
```bash
GET /api/prices/latest?symbol=BTC-USD
```

**Response** (200 OK):
```json
{
  "symbol": "BTC-USD",
  "timestamp": "2024-01-15T14:30:00Z",
  "price": 45678.90,
  "volume_24h": 29100000000,
  "high_24h": 46500.00,
  "low_24h": 42500.00,
  "bid": 45675.00,
  "ask": 45680.00,
  "source": "coinbase"
}
```

---

## Symbols

### List Supported Symbols

Get all cryptocurrency symbols supported by the system.

**Endpoint**: `GET /api/symbols`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "symbols": [
    {
      "symbol": "BTC-USD",
      "name": "Bitcoin",
      "base_currency": "BTC",
      "quote_currency": "USD",
      "active": true
    },
    {
      "symbol": "ETH-USD",
      "name": "Ethereum",
      "base_currency": "ETH",
      "quote_currency": "USD",
      "active": true
    },
    {
      "symbol": "SOL-USD",
      "name": "Solana",
      "base_currency": "SOL",
      "quote_currency": "USD",
      "active": true
    }
  ],
  "count": 20
}
```

---

## Configuration

### Get Detection Thresholds

Retrieve detection threshold configuration.

**Endpoint**: `GET /api/config/thresholds`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "global_defaults": {
    "z_score_threshold": 3.0,
    "min_absolute_return_threshold": 1.0
  },
  "volatility_tiers": {
    "stable": {
      "multiplier": 1.2,
      "assets": ["BTC-USD", "ETH-USD"]
    },
    "moderate": {
      "multiplier": 1.0,
      "assets": ["SOL-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "MATIC-USD"]
    },
    "volatile": {
      "multiplier": 0.7,
      "assets": ["DOGE-USD", "SHIB-USD", "PEPE-USD"]
    }
  },
  "asset_specific_thresholds": {
    "BTC-USD": {
      "z_score_threshold": 3.5,
      "min_absolute_return_threshold": 1.5
    },
    "DOGE-USD": {
      "z_score_threshold": 2.0,
      "min_absolute_return_threshold": 0.8
    }
  },
  "timeframes": {
    "enabled": true,
    "windows": [5, 15, 30, 60],
    "baseline_multiplier": 3
  }
}
```

---

### Get System Settings

Retrieve system configuration and feature flags.

**Endpoint**: `GET /api/config/settings`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "detection": {
    "enable_multi_timeframe": true,
    "use_asset_specific_thresholds": true,
    "timeframe_windows": [5, 15, 30, 60],
    "price_history_lookback_minutes": 240,
    "news_window_minutes": 30
  },
  "validation": {
    "pass_threshold": 0.65,
    "judge_llm_enabled": true,
    "parallel_validation": true
  },
  "news": {
    "mode": "live",
    "sources": ["rss", "grok"]
  },
  "llm": {
    "provider": "anthropic",
    "model": "claude-3-5-haiku-20241022"
  }
}
```

---

## Health Check

### System Health

Check API and database health.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T14:30:00.123Z",
  "database": "connected",
  "uptime_seconds": 123456,
  "version": "0.2.0"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "error",
  "timestamp": "2024-01-15T14:30:00.123Z",
  "database": "disconnected",
  "error": "Unable to connect to database"
}
```

---

## Statistics & Metrics

### Get System Metrics

Retrieve system performance metrics.

**Endpoint**: `GET /api/metrics`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "anomalies": {
    "total": 1543,
    "last_24h": 48,
    "by_type": {
      "price_spike": 420,
      "price_drop": 389,
      "volume_spike": 312,
      "combined": 422
    }
  },
  "narratives": {
    "total": 1543,
    "validated": 1164,
    "validation_rate": 0.754
  },
  "detection": {
    "average_z_score": 4.23,
    "average_confidence": 0.82
  },
  "performance": {
    "average_generation_time_seconds": 3.45,
    "average_validation_time_seconds": 0.85
  }
}
```

---

## Error Responses

### Standard Error Format

All error responses follow this format:

```json
{
  "error": "Error message",
  "details": "Additional context (optional)",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T14:30:00.123Z"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required or invalid |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource does not exist |
| 409 | Conflict - Resource already exists |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server-side error |
| 503 | Service Unavailable - Service temporarily down |

---

## Rate Limiting

### Rate Limit Headers

All API responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642257600
```

### Rate Limit Exceeded Response

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 45,
  "limit": 100,
  "window": "60 seconds"
}
```

---

## Pagination

### Pagination Parameters

All list endpoints support pagination:
- `limit` - Number of results per page (default: 20, max: 100)
- `offset` - Starting position (default: 0)

### Pagination Response

```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

---

## Filtering & Sorting

### Filter Operators

For advanced filtering (future):
- `gt` - Greater than: `?price_change_pct[gt]=-5.0`
- `lt` - Less than: `?confidence[lt]=0.9`
- `gte` - Greater than or equal
- `lte` - Less than or equal
- `in` - In list: `?symbol[in]=BTC-USD,ETH-USD`

### Sort Format

```
?sort_by=detected_at&sort_order=desc
?sort_by=confidence&sort_order=asc
```

---

## WebSocket Support (Future)

Real-time anomaly notifications via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:3001/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    symbols: ['BTC-USD', 'ETH-USD']
  }));
};

ws.onmessage = (event) => {
  const anomaly = JSON.parse(event.data);
  console.log('New anomaly detected:', anomaly);
};
```

---

## Example Client Implementation

### JavaScript/TypeScript

```typescript
class MANEClient {
  private baseURL: string;
  private token?: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async login(email: string, password: string) {
    const res = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Login failed');
    return await res.json();
  }

  async getAnomalies(params: AnomalyParams) {
    const query = new URLSearchParams(params as any).toString();
    const res = await fetch(`${this.baseURL}/api/anomalies?${query}`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch anomalies');
    return await res.json();
  }

  async getAnomalyDetails(id: string) {
    const res = await fetch(`${this.baseURL}/api/anomalies/${id}`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to fetch anomaly');
    return await res.json();
  }
}

// Usage
const client = new MANEClient('http://localhost:3001');
await client.login('user@example.com', 'password');
const anomalies = await client.getAnomalies({
  symbol: 'BTC-USD',
  limit: 10
});
```

### Python

```python
import requests

class MANEClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, email: str, password: str):
        res = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        res.raise_for_status()
        return res.json()

    def get_anomalies(self, **params):
        res = self.session.get(
            f"{self.base_url}/api/anomalies",
            params=params
        )
        res.raise_for_status()
        return res.json()

# Usage
client = MANEClient("http://localhost:3001")
client.login("user@example.com", "password")
anomalies = client.get_anomalies(symbol="BTC-USD", limit=10)
```

---

**See also**:
- Web Interface Documentation: `docs/WEB.md`
- Python API Documentation: `docs/API.md`
- Database Schema: `docs/DATABASE.md`
