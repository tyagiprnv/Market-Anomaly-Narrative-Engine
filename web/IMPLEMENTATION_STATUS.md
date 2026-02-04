# Web Application Implementation Status

## Overview

This document tracks the implementation progress of the Market Anomaly Narrative Engine web application.

**Current Phase:** Phase 1 - Backend Skeleton ✅ (Completed)
**Next Phase:** Phase 2 - Database Setup & Testing

---

## ✅ Completed Phases

### Phase 0: Planning & Setup
- [x] Created monorepo structure (`web/` directory)
- [x] Initialized package.json for backend, frontend, shared
- [x] Set up TypeScript configs for all packages
- [x] Created comprehensive README documentation

### Phase 1: Backend Skeleton
- [x] Express app setup with middleware (helmet, cors, cookie-parser)
- [x] Environment validation using Zod
- [x] Prisma database config (singleton pattern)
- [x] Logger setup (Winston)
- [x] Health check endpoint
- [x] Error handling middleware
- [x] Authentication middleware (JWT verification)
- [x] Rate limiting middleware
- [x] Validation middleware (Zod schemas)

### Phase 1.5: Shared Types & Constants
- [x] Enum definitions (AnomalyType, ValidationStatus, etc.)
- [x] Database DTOs (AnomalyDTO, NewsArticleDTO, etc.)
- [x] API request/response types
- [x] Supported symbols constants (20 crypto symbols)
- [x] Volatility tier mapping

### Phase 1.6: Authentication
- [x] Auth service (bcrypt password hashing, JWT generation)
- [x] Auth controller (register, login, logout, /me)
- [x] Auth routes with validation schemas
- [x] JWT utility functions
- [x] Rate limiting on auth endpoints

### Phase 1.7: Frontend Shell
- [x] Vite + React setup
- [x] Tailwind CSS configuration
- [x] React Router setup
- [x] Auth context with React Query integration
- [x] API client (Axios with interceptors)
- [x] TanStack Query provider
- [x] Basic login/register pages
- [x] Protected route wrapper

### Phase 1.8: Utility Functions
- [x] Pagination utilities
- [x] Query key factory (React Query)
- [x] Formatters (date, price, percent, etc.)
- [x] Color utilities for badges

---

## 🚧 In Progress

### Phase 2: Database Setup & Testing
- [ ] Run SQL migration to add `users` table
- [ ] Introspect database schema with Prisma (`npx prisma db pull`)
- [ ] Generate Prisma client (`npx prisma generate`)
- [ ] Test backend startup and health endpoint
- [ ] Test authentication flow (register → login → /me)

---

## 📋 Upcoming Phases

### Phase 3: Core API - Anomalies (Estimated: 3 days)
- [ ] Anomaly service (Prisma queries with filters)
- [ ] DTO transformers (DB model → API response)
- [ ] GET /api/anomalies (filters: symbol, date range, type, validation, pagination)
- [ ] GET /api/anomalies/:id (eager load news, narrative, clusters)
- [ ] GET /api/anomalies/latest (efficient polling query)
- [ ] GET /api/anomalies/stats
- [ ] Anomaly controller and routes
- [ ] Test coverage (unit + integration)

### Phase 4: Core API - News & Prices (Estimated: 2 days)
- [ ] News service (queries + clustering logic)
- [ ] GET /api/news (filters)
- [ ] GET /api/news/clusters/:anomalyId
- [ ] Price service (history with auto-aggregation)
- [ ] GET /api/prices/:symbol
- [ ] Test coverage

### Phase 5: Config & Symbols API (Estimated: 1 day)
- [ ] Thresholds service (parse `config/thresholds.yaml`)
- [ ] GET /api/symbols (with tier info)
- [ ] GET /api/symbols/:symbol/stats
- [ ] GET /api/config/thresholds
- [ ] Test YAML parsing

### Phase 6: Dashboard Page (Estimated: 3 days)
- [ ] Query hooks (useAnomalies, useLatestAnomalies with 30s polling)
- [ ] Dashboard page layout
- [ ] AnomalyCard component
- [ ] AnomalyList component
- [ ] Symbol selector (multi-select)
- [ ] Live indicator (last update time)

### Phase 7: Anomaly Detail View (Estimated: 2 days)
- [ ] useAnomalyDetail hook
- [ ] AnomalyDetail page layout
- [ ] AnomalyDetailPanel (metrics, metadata)
- [ ] NarrativeDisplay component
- [ ] ValidationBadge component
- [ ] NewsClusterView component
- [ ] NewsArticleCard component

### Phase 8: Price Charts (Estimated: 3 days)
- [ ] Lightweight Charts integration
- [ ] usePriceHistory hook
- [ ] PriceChart component (line chart)
- [ ] Anomaly markers on chart
- [ ] Custom tooltip
- [ ] ChartView page (full-screen)
- [ ] Responsive chart container

### Phase 9: Historical Browser (Estimated: 2 days)
- [ ] HistoricalBrowser page
- [ ] AnomalyFilters component
- [ ] URL state management
- [ ] Pagination component
- [ ] Filter persistence (localStorage)

### Phase 10: Polish & UX (Estimated: 2 days)
- [ ] Error boundaries
- [ ] Loading states (skeleton loaders)
- [ ] Empty states
- [ ] Toast notifications
- [ ] Responsive design
- [ ] Accessibility improvements

### Phase 11: Testing (Estimated: 3 days)
- [ ] Backend unit tests (services, transformers)
- [ ] Backend integration tests (API routes)
- [ ] Frontend unit tests (components)
- [ ] E2E tests (Playwright)
- [ ] Test coverage reports

### Phase 12: Docker & Deployment (Estimated: 2 days)
- [ ] Backend Dockerfile
- [ ] Frontend Dockerfile (Vite build → nginx)
- [ ] Update docker-compose.yml
- [ ] Environment variable management
- [ ] Test Docker deployment locally

---

## File Structure

### Backend (`web/backend/`)
```
src/
├── config/
│   ├── env.ts ✅
│   └── database.ts ✅
├── middleware/
│   ├── auth.ts ✅
│   ├── errorHandler.ts ✅
│   ├── validation.ts ✅
│   └── rateLimit.ts ✅
├── routes/
│   ├── auth.routes.ts ✅
│   └── health.routes.ts ✅
├── controllers/
│   └── auth.controller.ts ✅
├── services/
│   └── auth.service.ts ✅
├── utils/
│   ├── logger.ts ✅
│   ├── jwt.ts ✅
│   └── pagination.ts ✅
└── index.ts ✅
```

### Frontend (`web/frontend/`)
```
src/
├── api/
│   ├── client.ts ✅
│   └── queries/ (empty)
├── context/
│   └── AuthContext.tsx ✅
├── utils/
│   ├── queryKeys.ts ✅
│   └── formatters.ts ✅
├── components/ (empty - to be implemented)
├── pages/ (empty - basic login/register in App.tsx)
├── App.tsx ✅
├── main.tsx ✅
└── index.css ✅
```

### Shared (`web/shared/`)
```
types/
├── enums.ts ✅
├── database.ts ✅
└── api.ts ✅
constants/
├── symbols.ts ✅
└── thresholds.ts ✅
index.ts ✅
```

---

## Next Steps

1. **Database Setup**
   ```bash
   # Connect to PostgreSQL
   psql -U mane_user -d mane_db

   # Run migration
   \i web/backend/migrations/001_add_users_table.sql

   # Exit psql
   \q
   ```

2. **Backend Setup**
   ```bash
   cd web/backend
   npm install
   cp .env.example .env
   # Edit .env with your database credentials and JWT_SECRET
   npm run prisma:pull
   npm run prisma:generate
   npm run dev
   ```

3. **Frontend Setup**
   ```bash
   cd web/frontend
   npm install
   cp .env.example .env
   # Edit .env with backend URL
   npm run dev
   ```

4. **Test Authentication**
   - Visit http://localhost:5173/register
   - Create an account
   - Verify login works
   - Check backend logs for auth requests

---

## Notes

- **Database Ownership:** Python pipeline owns schema. Web app uses Prisma introspection.
- **Polling Strategy:** 30-second HTTP polling for real-time updates.
- **Authentication:** 24-hour JWT in httpOnly cookie.
- **Chart Library:** Lightweight Charts (TradingView) for performance.

---

## Estimated Timeline

- **Completed:** ~5 days (Phase 0-1.8)
- **Remaining:** ~18-23 days (Phase 2-12)
- **Total:** ~6-7 weeks for full-featured MVP

---

## Links

- [Main README](./README.md) - Complete setup and usage guide
- [Implementation Plan](../CLAUDE.md) - Full implementation plan (if saved)
- [Backend Package](./backend/package.json) - Backend dependencies
- [Frontend Package](./frontend/package.json) - Frontend dependencies
