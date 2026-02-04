# Phase 4 Testing Guide - News & Prices API

## Overview

Phase 4 adds two new API endpoint groups:
1. **News API** - Query news articles and clusters
2. **Prices API** - Query price history with auto-aggregation

All endpoints require authentication (JWT cookie from `/api/auth/login`).

## Setup

1. Start the backend server:
```bash
cd web/backend
npm run dev
```

2. Register/login to get authentication cookie:
```bash
# Register
curl -X POST http://localhost:4000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"testpass123"}' \
  -c /tmp/cookies.txt

# Or login if already registered
curl -X POST http://localhost:4000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com","password":"testpass123"}' \
  -c /tmp/cookies.txt
```

## News API Endpoints

### GET /api/news
Get all news articles with optional filters and pagination.

**Query Parameters:**
- `page` (optional, default: 1) - Page number
- `limit` (optional, default: 20, max: 100) - Items per page
- `symbol` (optional) - Filter by symbol (e.g., "BTC-USD")
- `anomalyId` (optional) - Filter by anomaly UUID
- `startDate` (optional) - ISO date string (e.g., "2026-02-04")
- `endDate` (optional) - ISO date string

**Examples:**
```bash
# Get all news articles (paginated)
curl -s http://localhost:4000/api/news -b /tmp/cookies.txt | jq

# Get news for specific symbol
curl -s 'http://localhost:4000/api/news?symbol=BTC-USD' -b /tmp/cookies.txt | jq

# Get news with date range
curl -s 'http://localhost:4000/api/news?startDate=2026-02-01&endDate=2026-02-04' -b /tmp/cookies.txt | jq

# Paginated request
curl -s 'http://localhost:4000/api/news?page=1&limit=10' -b /tmp/cookies.txt | jq
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "anomalyId": "uuid",
      "title": "News article title",
      "url": "https://...",
      "source": "coindesk",
      "publishedAt": "2026-02-04T18:00:00.000Z",
      "sentiment": "POSITIVE",
      "timing": "BEFORE",
      "clusterId": "1",
      "createdAt": "2026-02-04T18:00:00.000Z"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5,
    "hasNext": true,
    "hasPrev": false
  }
}
```

### GET /api/news/clusters/:anomalyId
Get news clusters for a specific anomaly with their articles.

**Path Parameters:**
- `anomalyId` (required) - Anomaly UUID

**Example:**
```bash
# First get an anomaly ID
ANOMALY_ID=$(curl -s 'http://localhost:4000/api/anomalies?limit=1' -b /tmp/cookies.txt | jq -r '.data[0].id')

# Get clusters for that anomaly
curl -s "http://localhost:4000/api/news/clusters/$ANOMALY_ID" -b /tmp/cookies.txt | jq
```

**Response:**
```json
[
  {
    "id": "uuid",
    "anomalyId": "uuid",
    "clusterLabel": "Bitcoin price surge",
    "articleCount": 5,
    "averageSentiment": "POSITIVE",
    "createdAt": "2026-02-04T18:00:00.000Z",
    "articles": [
      {
        "id": "uuid",
        "title": "...",
        ...
      }
    ]
  }
]
```

## Prices API Endpoints

### GET /api/prices/:symbol
Get price history for a symbol with auto-aggregation.

**Path Parameters:**
- `symbol` (required) - Symbol (e.g., "BTC-USD")

**Query Parameters:**
- `startDate` (optional) - ISO date string (defaults to 24 hours ago)
- `endDate` (optional) - ISO date string (defaults to now)
- `aggregation` (optional, default: "auto") - Aggregation level: "auto", "1m", "5m", "1h", "1d"

**Auto-Aggregation Logic:**
- < 24 hours: 1-minute data (raw)
- 1-7 days: 5-minute aggregation
- 7-30 days: 1-hour aggregation
- > 30 days: 1-day aggregation

**Examples:**
```bash
# Get recent price history (auto-aggregation, last 24h)
curl -s http://localhost:4000/api/prices/BTC-USD -b /tmp/cookies.txt | jq '.[0:5]'

# Get 1-minute data
curl -s 'http://localhost:4000/api/prices/BTC-USD?aggregation=1m' -b /tmp/cookies.txt | jq '.[0:5]'

# Get 1-hour data
curl -s 'http://localhost:4000/api/prices/BTC-USD?aggregation=1h' -b /tmp/cookies.txt | jq '.[0:5]'

# Get price history with date range
curl -s 'http://localhost:4000/api/prices/BTC-USD?startDate=2026-02-01&endDate=2026-02-04' \
  -b /tmp/cookies.txt | jq '.[0:5]'
```

**Response:**
```json
[
  {
    "timestamp": "2026-02-04T18:00:00.000Z",
    "symbol": "BTC-USD",
    "price": 95300,
    "volume": 1800000000
  },
  {
    "timestamp": "2026-02-04T18:01:00.000Z",
    "symbol": "BTC-USD",
    "price": 95350,
    "volume": 1850000000
  }
]
```

### GET /api/prices/:symbol/latest
Get the latest price for a symbol.

**Path Parameters:**
- `symbol` (required) - Symbol (e.g., "BTC-USD")

**Example:**
```bash
curl -s http://localhost:4000/api/prices/BTC-USD/latest -b /tmp/cookies.txt | jq
```

**Response:**
```json
{
  "timestamp": "2026-02-04T18:27:04.256Z",
  "symbol": "BTC-USD",
  "price": 95300,
  "volume": 1800000000
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message"
}
```

**Common Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

**Examples:**
```bash
# Invalid symbol
curl -s http://localhost:4000/api/prices/INVALID/latest -b /tmp/cookies.txt | jq
# => {"error": "NotFound", "message": "No price data found for symbol INVALID"}

# Missing authentication
curl -s http://localhost:4000/api/news | jq
# => {"error": "UnauthorizedError", "message": "No token provided"}

# Invalid UUID
curl -s http://localhost:4000/api/news/clusters/invalid-uuid -b /tmp/cookies.txt | jq
# => {"error": "ValidationError", "message": "Invalid request data"}
```

## Implementation Details

### Files Created/Modified

**Services:**
- `src/services/news.service.ts` - News queries with filters
- `src/services/price.service.ts` - Price queries with auto-aggregation

**Controllers:**
- `src/controllers/news.controller.ts` - HTTP request handlers
- `src/controllers/price.controller.ts` - HTTP request handlers

**Routes:**
- `src/routes/news.routes.ts` - News endpoint definitions
- `src/routes/price.routes.ts` - Price endpoint definitions

**Schemas:**
- `src/schemas/news.schemas.ts` - Zod validation schemas
- `src/schemas/price.schemas.ts` - Zod validation schemas

**Transformers:**
- `src/transformers/price.transformer.ts` - DB model to DTO conversion

**Main App:**
- `src/index.ts` - Registered new routes

### Key Features

1. **Auto-Aggregation**: Price API automatically selects appropriate aggregation level based on date range
2. **Efficient Queries**: Uses Prisma for type-safe database queries
3. **Pagination**: Consistent pagination across all list endpoints
4. **Validation**: Zod schemas validate all query parameters and path parameters
5. **Authentication**: All endpoints protected with JWT middleware
6. **Error Handling**: Consistent error responses with proper HTTP status codes

## Next Steps

Phase 5 will implement:
- Threshold configuration API (read from `config/thresholds.yaml`)
- Symbols API with volatility tier information
- Symbol statistics API
