# Market Anomaly Narrative Engine - Web Application

Full-featured web application for monitoring crypto price anomalies with real-time updates, interactive charts, and AI-generated narratives.

## Tech Stack

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query
- **Backend:** Express.js + TypeScript + Prisma ORM
- **Database:** PostgreSQL (shared with Python pipeline)
- **Charts:** Lightweight Charts (TradingView)
- **Auth:** JWT with httpOnly cookies

## Project Structure

```
web/
├── shared/          # Shared TypeScript types and constants
├── backend/         # Express API server
└── frontend/        # React UI application
```

## Prerequisites

- Node.js 20+ and npm
- PostgreSQL database (already set up for Python pipeline)
- Python pipeline running (for detecting anomalies)

## Quick Start

### 1. Database Setup

First, add the users table to your existing PostgreSQL database:

```bash
# Connect to your database
psql -U mane_user -d mane_db

# Run the migration
\i web/backend/migrations/001_add_users_table.sql
```

### 2. Backend Setup

```bash
cd web/backend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env with your database credentials
# DATABASE_URL=postgresql://mane_user:password@localhost:5432/mane_db
# JWT_SECRET=<generate-a-random-secret-key>

# Introspect database schema (generates Prisma client)
npm run prisma:pull
npm run prisma:generate

# Start development server
npm run dev
```

Backend will run on `http://localhost:4000`

### 3. Frontend Setup

```bash
cd web/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env to point to backend
# VITE_API_URL=http://localhost:4000/api

# Start development server
npm run dev
```

Frontend will run on `http://localhost:5173`

### 4. Verify Installation

1. Visit `http://localhost:4000/api/health` - should return `{"status": "ok"}`
2. Visit `http://localhost:5173` - should show login page
3. Register a new account
4. Start the Python detection pipeline to populate data

## Development Workflow

### Backend Development

```bash
cd web/backend

npm run dev          # Start dev server with hot reload
npm run test         # Run tests
npm run test:watch   # Run tests in watch mode
npm run lint         # Lint TypeScript files
npm run type-check   # Check TypeScript types

# Prisma commands
npm run prisma:studio   # Open Prisma Studio GUI
npm run prisma:pull     # Re-introspect database schema
npm run prisma:generate # Regenerate Prisma client
```

### Frontend Development

```bash
cd web/frontend

npm run dev          # Start dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run test         # Run unit tests
npm run test:e2e     # Run E2E tests with Playwright
npm run lint         # Lint TypeScript files
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Login (sets JWT cookie)
- `POST /api/auth/logout` - Logout (clears cookie)
- `GET /api/auth/me` - Get current user

### Anomalies
- `GET /api/anomalies` - List anomalies with filters
- `GET /api/anomalies/:id` - Get anomaly details
- `GET /api/anomalies/latest` - Polling endpoint (new since timestamp)
- `GET /api/anomalies/stats` - Summary statistics

### News
- `GET /api/news` - List news articles
- `GET /api/news/clusters/:anomalyId` - Get news clusters for anomaly

### Prices
- `GET /api/prices/:symbol` - Get price history with auto-aggregation

### Symbols & Config
- `GET /api/symbols` - List supported symbols
- `GET /api/symbols/:symbol/stats` - Get symbol statistics
- `GET /api/config/thresholds` - Get threshold configuration

### Health
- `GET /api/health` - Health check

## Key Features

### 1. Real-Time Dashboard
- Live anomaly feed with 30-second polling
- Symbol filtering (multi-select)
- Anomaly type filtering
- Validation status badges

### 2. Anomaly Detail View
- Full statistical metrics (Z-score, price change %, volume change %)
- Detection metadata (timeframe, volatility tier, threshold used)
- AI-generated narrative with confidence score
- Validation status and reason
- Interactive price chart with anomaly markers
- Grouped news clusters with sentiment analysis

### 3. Interactive Charts
- Lightweight Charts (TradingView) integration
- Anomaly markers color-coded by type (spike/drop)
- Custom tooltips on hover
- Multiple timeframes (5min, 15min, 30min, 60min)
- Auto-aggregation for long time ranges

### 4. News Clustering
- Grouped articles by semantic similarity
- Sentiment color coding (positive/negative/neutral)
- Timing badges (before/during/after anomaly)
- Expandable clusters with article counts

### 5. Historical Browser
- Search and filter anomalies
- Date range picker
- Symbol filter
- Type filter
- Validation status filter
- Pagination with URL state

## Configuration

### Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/database

# JWT
JWT_SECRET=your-secret-key-min-32-chars

# Server
PORT=4000
NODE_ENV=development

# CORS
FRONTEND_URL=http://localhost:5173

# Logging
LOG_LEVEL=info
```

### Frontend Environment Variables

```bash
# API URL
VITE_API_URL=http://localhost:4000/api
```

## Testing

### Backend Tests

```bash
cd web/backend

# Unit tests
npm run test

# Integration tests with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

### Frontend Tests

```bash
cd web/frontend

# Unit tests (Vitest + React Testing Library)
npm run test

# E2E tests (Playwright)
npm run test:e2e

# E2E with UI
npm run test:e2e:ui
```

## Database Schema

The web app uses the existing database schema from the Python pipeline:

- `prices` - Time-series price data
- `anomalies` - Detected anomalies with metrics
- `news_articles` - News articles linked to anomalies
- `narratives` - AI-generated narratives
- `news_clusters` - Grouped news articles
- `users` - **New table for authentication**

**Important:** The Python pipeline owns the schema. The web app uses Prisma introspection (read-only). To update the schema, modify the Python SQLAlchemy models and re-run `npm run prisma:pull` in the backend.

## Deployment

### Docker Deployment (Coming Soon)

```bash
# Build and run all services
docker-compose up --build

# Services:
# - PostgreSQL: localhost:5433
# - Backend: localhost:4000
# - Frontend: localhost:3000
```

### Production Checklist

- [ ] Set `NODE_ENV=production`
- [ ] Generate strong `JWT_SECRET` (256-bit random string)
- [ ] Enable HTTPS (required for secure cookies)
- [ ] Update `FRONTEND_URL` to production domain
- [ ] Configure CORS for production domain
- [ ] Set up proper logging (Winston file transports)
- [ ] Enable database connection pooling
- [ ] Configure rate limiting for production traffic
- [ ] Set up monitoring and alerts

## Troubleshooting

### Backend won't start

1. Check database connection: `psql -U mane_user -d mane_db`
2. Verify environment variables in `.env`
3. Run `npm run prisma:pull` to sync schema
4. Check logs in `logs/` directory

### Frontend can't connect to backend

1. Verify backend is running: `curl http://localhost:4000/api/health`
2. Check `VITE_API_URL` in frontend `.env`
3. Verify CORS configuration in backend

### No anomalies showing up

1. Ensure Python detection pipeline is running
2. Check database has anomalies: `SELECT COUNT(*) FROM anomalies;`
3. Verify backend can query database (check `/api/anomalies`)

### Prisma schema out of sync

```bash
cd web/backend
npm run prisma:pull      # Re-introspect database
npm run prisma:generate  # Regenerate client
```

## Contributing

1. Follow existing code structure
2. Run linters before committing: `npm run lint`
3. Write tests for new features
4. Update TypeScript types in `shared/` if adding new fields
5. Document new API endpoints in this README

## Architecture Notes

### Polling Strategy

The app uses HTTP polling (30-second intervals) for real-time updates. This is simpler than WebSockets and works through firewalls. The backend optimizes polling with:

- Efficient queries (only fetch anomalies newer than last poll)
- Database indexes on `detected_at`
- Early return if no new data

### Chart Data Aggregation

For long time ranges, the backend auto-aggregates price data:

- ≤4 hours: 1-minute data
- ≤24 hours: 5-minute data
- ≤7 days: 15-minute data
- >7 days: 1-hour data

This keeps charts performant while maintaining detail at relevant zoom levels.

### Authentication Flow

1. User submits email/password → `POST /api/auth/login`
2. Server verifies with bcrypt, generates 24-hour JWT
3. JWT stored in httpOnly cookie (SameSite=Strict, Secure in production)
4. Frontend includes cookie automatically on all requests
5. Backend middleware verifies JWT on protected routes

## License

MIT
