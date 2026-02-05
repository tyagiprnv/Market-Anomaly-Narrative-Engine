# Web Interface Documentation

## Overview

The Market Anomaly Narrative Engine includes a **production-ready full-stack web application** for monitoring cryptocurrency anomalies in real-time. The web interface provides a modern, responsive UI for viewing detected anomalies, generated narratives, validation results, and historical data.

**Tech Stack**:
- **Frontend**: React 18 + TypeScript + TailwindCSS + Vite
- **Backend**: Express + TypeScript + Prisma ORM + JWT Authentication
- **Charts**: TradingView Lightweight Charts
- **State Management**: TanStack Query (React Query)
- **Database**: Prisma introspects Python-owned PostgreSQL schema

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ Dashboard  │  │  Anomaly   │  │ Historical │             │
│  │   Live     │  │  Detail    │  │  Browser   │             │
│  │  Feed      │  │  View      │  │  Archive   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
│         │              │              │                      │
│         └──────────────┴──────────────┘                      │
│                        │                                     │
│                  TanStack Query                              │
│                        │                                     │
└────────────────────────┼─────────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────┼─────────────────────────────────────┐
│                  Backend (Express)                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │    Auth    │  │  Anomaly   │  │   Price    │             │
│  │   Routes   │  │   Routes   │  │   Routes   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
│         │              │              │                      │
│         └──────────────┴──────────────┘                      │
│                        │                                     │
│                   Prisma ORM                                 │
│                        │                                     │
└────────────────────────┼─────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────┐
│               PostgreSQL Database                            │
│  (Schema owned by Python/SQLAlchemy)                         │
└──────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

### Project Structure

```
web/frontend/
├── src/
│   ├── main.tsx               # Entry point
│   ├── App.tsx                # Root component with routing
│   ├── pages/                 # Page components
│   │   ├── Dashboard.tsx          # Live anomaly feed (auto-refresh)
│   │   ├── AnomalyDetail.tsx      # Detailed anomaly view
│   │   ├── ChartView.tsx          # Price charts
│   │   └── HistoricalBrowser.tsx  # Searchable archive
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── LiveIndicator.tsx      # Live status indicator
│   │   │   ├── SymbolSelector.tsx     # Multi-symbol filter
│   │   │   └── AnomalyCard.tsx        # Anomaly display card
│   │   ├── charts/
│   │   │   ├── PriceChart.tsx         # TradingView chart wrapper
│   │   │   └── TimeRangeSelector.tsx  # Time range controls
│   │   ├── browser/
│   │   │   ├── Filters.tsx            # Advanced filtering
│   │   │   └── Pagination.tsx         # Page navigation
│   │   └── common/
│   │       ├── LoadingSkeleton.tsx    # Loading states
│   │       ├── ErrorBoundary.tsx      # Error handling
│   │       └── Toast.tsx              # Notifications
│   ├── hooks/
│   │   ├── useAnomalies.ts        # Anomaly data fetching
│   │   ├── usePrices.ts           # Price data fetching
│   │   └── useAuth.ts             # Authentication logic
│   ├── lib/
│   │   ├── api.ts                 # API client
│   │   └── types.ts               # TypeScript types
│   └── styles/
│       └── globals.css            # Global styles + Tailwind
├── public/                    # Static assets
├── index.html                 # HTML template
├── package.json               # Dependencies
├── tsconfig.json              # TypeScript config
├── vite.config.ts             # Vite config
└── tailwind.config.js         # Tailwind CSS config
```

### Key Features

#### 1. Dashboard (Real-Time Monitoring)

**Component**: `pages/Dashboard.tsx`

**Features**:
- Auto-refreshing anomaly feed (configurable interval)
- Live status indicator (connected/disconnected)
- Symbol filtering (BTC, ETH, SOL, etc.)
- Anomaly type filtering (price_spike, price_drop, volume_spike, combined)
- Validation status filtering (validated only, all)
- Infinite scroll with pagination
- Real-time updates using TanStack Query

**Example Usage**:
```typescript
import { useAnomalies } from '../hooks/useAnomalies';

function Dashboard() {
  const { data, isLoading, refetch } = useAnomalies({
    limit: 20,
    symbol: 'BTC-USD',
    validated: true,
  });

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(refetch, 30000);
    return () => clearInterval(interval);
  }, [refetch]);

  return (
    <div>
      <LiveIndicator connected={!isLoading} />
      {data?.anomalies.map(anomaly => (
        <AnomalyCard key={anomaly.id} anomaly={anomaly} />
      ))}
    </div>
  );
}
```

#### 2. Anomaly Detail View

**Component**: `pages/AnomalyDetail.tsx`

**Features**:
- Full anomaly details (type, confidence, z-score, price change)
- Generated narrative with metadata
- Validation results (passed/failed, reason, score)
- Tool usage tracking (which agent tools were called)
- News articles linked to anomaly
- News clustering visualization
- Price chart with anomaly timestamp marker
- Export functionality (JSON, CSV)

**URL**: `/anomaly/:id`

#### 3. Interactive Charts

**Component**: `pages/ChartView.tsx` + `components/charts/PriceChart.tsx`

**Features**:
- TradingView Lightweight Charts integration
- Multiple timeframes (1H, 4H, 1D, 1W, 1M)
- Candlestick chart with volume
- Anomaly markers on timeline
- Zoom and pan controls
- Real-time price updates
- Export chart as image

**Implementation**:
```typescript
import { createChart } from 'lightweight-charts';

function PriceChart({ symbol, anomalyTimestamp }) {
  const chartRef = useRef(null);

  useEffect(() => {
    const chart = createChart(chartRef.current, {
      width: 800,
      height: 400,
      layout: { backgroundColor: '#FFFFFF' },
    });

    const candlestickSeries = chart.addCandlestickSeries();

    // Fetch and set price data
    // ...

    // Add anomaly marker
    candlestickSeries.setMarkers([{
      time: anomalyTimestamp,
      position: 'aboveBar',
      color: '#f44336',
      shape: 'arrowDown',
      text: 'Anomaly',
    }]);
  }, [symbol, anomalyTimestamp]);

  return <div ref={chartRef} />;
}
```

#### 4. Historical Browser

**Component**: `pages/HistoricalBrowser.tsx`

**Features**:
- Searchable archive of all anomalies
- Advanced filtering:
  - Symbol selection
  - Date range picker
  - Anomaly type filter
  - Validation status filter
  - Confidence threshold slider
- Sorting options (date, confidence, price change)
- Pagination with page size control
- Export search results
- Bulk actions (mark as reviewed, etc.)

### State Management

**TanStack Query** (React Query) handles all server state:

```typescript
// hooks/useAnomalies.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useAnomalies(params: AnomalyParams) {
  return useQuery({
    queryKey: ['anomalies', params],
    queryFn: () => api.getAnomalies(params),
    staleTime: 30000, // 30 seconds
    refetchInterval: 30000, // Auto-refresh
  });
}
```

**React Context** for authentication:

```typescript
// App.tsx
const AuthContext = createContext<AuthContextType>(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

## Backend Architecture

### Project Structure

```
web/backend/
├── src/
│   ├── index.ts               # Express app entry point
│   ├── routes/
│   │   ├── auth.routes.ts         # /auth/* endpoints
│   │   ├── anomaly.routes.ts      # /api/anomalies/* endpoints
│   │   ├── news.routes.ts         # /api/news/* endpoints
│   │   ├── price.routes.ts        # /api/prices/* endpoints
│   │   ├── symbols.routes.ts      # /api/symbols/* endpoints
│   │   ├── config.routes.ts       # /api/config/* endpoints
│   │   └── health.routes.ts       # /health endpoint
│   ├── middleware/
│   │   ├── auth.middleware.ts     # JWT verification
│   │   ├── error.middleware.ts    # Error handling
│   │   └── rateLimiter.middleware.ts  # Rate limiting
│   ├── lib/
│   │   ├── prisma.ts              # Prisma client singleton
│   │   ├── jwt.ts                 # JWT utilities
│   │   └── logger.ts              # Winston logger
│   └── types/
│       └── index.ts               # TypeScript types
├── prisma/
│   └── schema.prisma          # Prisma schema (introspected from DB)
├── package.json               # Dependencies
├── tsconfig.json              # TypeScript config
└── .env                       # Environment variables
```

### API Endpoints

#### 1. Authentication (`/auth`)

```typescript
// POST /auth/register
{
  "username": "string",
  "email": "string",
  "password": "string"
}
→ { "message": "Registration successful" }

// POST /auth/login
{
  "email": "string",
  "password": "string"
}
→ Sets httpOnly cookie with JWT token
→ { "user": { "id": "...", "email": "...", "username": "..." } }

// POST /auth/logout
→ Clears cookie
→ { "message": "Logged out successfully" }

// GET /auth/me
→ { "user": { ... } } or 401 if not authenticated
```

**Implementation**:
```typescript
// routes/auth.routes.ts
router.post('/login', async (req, res) => {
  const { email, password } = req.body;

  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });

  const isValid = await bcrypt.compare(password, user.password_hash);
  if (!isValid) return res.status(401).json({ error: 'Invalid credentials' });

  const token = jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: '7d' });

  res.cookie('auth_token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
  });

  res.json({ user: { id: user.id, email: user.email, username: user.username } });
});
```

#### 2. Anomalies (`/api/anomalies`)

```typescript
// GET /api/anomalies
Query params:
  - limit: number (default: 20)
  - offset: number (default: 0)
  - symbol: string (optional)
  - validated: boolean (optional)
  - startDate: ISO string (optional)
  - endDate: ISO string (optional)

→ {
  "anomalies": [
    {
      "id": "uuid",
      "symbol": "BTC-USD",
      "detected_at": "2024-01-15T14:15:00Z",
      "anomaly_type": "price_drop",
      "z_score": -3.87,
      "price_change_pct": -5.2,
      "confidence": 0.89,
      "detection_metadata": {
        "timeframe_minutes": 60,
        "volatility_tier": "stable",
        "asset_threshold": 3.5
      },
      "narrative": {
        "id": "uuid",
        "narrative_text": "Bitcoin dropped 5.2%...",
        "validation_passed": true,
        "validation_score": 0.78,
        "tools_used": ["verify_timestamp", "sentiment_check"]
      }
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}

// GET /api/anomalies/:id
→ { "anomaly": { ... }, "news": [...], "prices": [...] }
```

#### 3. News (`/api/news`)

```typescript
// GET /api/news
Query params:
  - anomalyId: string (optional)
  - symbol: string (optional)
  - limit: number (default: 50)

→ {
  "articles": [
    {
      "id": "uuid",
      "title": "Bitcoin drops on SEC news",
      "source": "CoinDesk",
      "published_at": "2024-01-15T14:05:00Z",
      "timing_tag": "pre_event",
      "time_diff_minutes": -10.0,
      "sentiment": "negative",
      "cluster_id": 1
    }
  ]
}
```

#### 4. Prices (`/api/prices`)

```typescript
// GET /api/prices
Query params:
  - symbol: string (required)
  - startDate: ISO string (required)
  - endDate: ISO string (required)
  - interval: "1m" | "5m" | "15m" | "1h" | "1d" (default: "1m")

→ {
  "prices": [
    {
      "timestamp": "2024-01-15T14:00:00Z",
      "price": 45000.50,
      "volume_24h": 1234567890,
      "high_24h": 46000,
      "low_24h": 44000
    }
  ]
}
```

#### 5. Symbols (`/api/symbols`)

```typescript
// GET /api/symbols
→ {
  "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", ...]
}
```

#### 6. Config (`/api/config`)

```typescript
// GET /api/config/thresholds
→ {
  "global_defaults": { "z_score_threshold": 3.0 },
  "volatility_tiers": {
    "stable": { "multiplier": 1.2, "assets": ["BTC-USD", "ETH-USD"] },
    "moderate": { "multiplier": 1.0, "assets": [...] },
    "volatile": { "multiplier": 0.7, "assets": ["DOGE-USD", ...] }
  },
  "asset_specific_thresholds": {
    "BTC-USD": { "z_score_threshold": 3.5 }
  }
}
```

#### 7. Health (`/health`)

```typescript
// GET /health
→ {
  "status": "ok",
  "timestamp": "2024-01-15T14:15:00Z",
  "database": "connected",
  "uptime": 123456
}
```

### Middleware

#### Authentication

```typescript
// middleware/auth.middleware.ts
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const token = req.cookies.auth_token;
  if (!token) return res.status(401).json({ error: 'Unauthorized' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.userId;
    next();
  } catch (err) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// Usage:
router.get('/api/anomalies', requireAuth, getAnomalies);
```

#### Rate Limiting

```typescript
// middleware/rateLimiter.middleware.ts
import rateLimit from 'express-rate-limit';

export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 requests per window
  message: 'Too many authentication attempts',
});

export const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute
});

// Usage:
router.post('/auth/login', authLimiter, login);
router.get('/api/*', apiLimiter, ...);
```

#### Error Handling

```typescript
// middleware/error.middleware.ts
export function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  logger.error('Error:', err);

  if (err instanceof PrismaClientKnownRequestError) {
    return res.status(400).json({ error: 'Database error', details: err.message });
  }

  res.status(500).json({ error: 'Internal server error' });
}

// Usage (in index.ts):
app.use(errorHandler);
```

### Prisma Setup

**Prisma** introspects the Python-owned PostgreSQL schema and generates TypeScript types.

**Schema Generation**:
```bash
# 1. Introspect existing database (Python-owned schema)
npx prisma db pull

# 2. Generate Prisma client
npx prisma generate
```

**Generated Schema** (`prisma/schema.prisma`):
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Price {
  id         Int      @id @default(autoincrement())
  symbol     String   @db.VarChar(20)
  timestamp  DateTime
  price      Float
  volume_24h Float?
  created_at DateTime @default(now())

  @@index([symbol, timestamp])
  @@map("prices")
}

model Anomaly {
  id                  String    @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  symbol              String    @db.VarChar(20)
  detected_at         DateTime
  anomaly_type        String    @db.VarChar(20)
  z_score             Float?
  price_change_pct    Float?
  confidence          Float?
  detection_metadata  Json?

  narrative           Narrative?
  news_articles       NewsArticle[]
  news_clusters       NewsCluster[]

  @@index([symbol, detected_at])
  @@map("anomalies")
}

model Narrative {
  id                      String   @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  anomaly_id              String   @unique @db.Uuid
  narrative_text          String
  validation_passed       Boolean?
  validation_reason       String?
  tools_used              Json?
  llm_provider            String?

  anomaly                 Anomaly  @relation(fields: [anomaly_id], references: [id], onDelete: Cascade)

  @@map("narratives")
}

// ... other models
```

**Usage**:
```typescript
// lib/prisma.ts
import { PrismaClient } from '@prisma/client';

export const prisma = new PrismaClient();

// In routes:
const anomalies = await prisma.anomaly.findMany({
  where: { symbol: 'BTC-USD' },
  include: { narrative: true, news_articles: true },
  orderBy: { detected_at: 'desc' },
  take: 20,
});
```

## Development Workflow

### Prerequisites

- Node.js 18+ (`node --version`)
- npm or pnpm (`npm --version`)
- PostgreSQL running (with Python schema already created)

### Setup

```bash
# 1. Install dependencies
cd web/backend && npm install
cd ../frontend && npm install

# 2. Configure environment
# web/backend/.env
DATABASE_URL="postgresql://user:pass@localhost:5432/mane_db"
JWT_SECRET="your-secret-key-change-in-production"
NODE_ENV="development"

# 3. Generate Prisma client (introspect Python schema)
cd web/backend
npx prisma db pull      # Pulls schema from database
npx prisma generate     # Generates TypeScript client

# 4. Start development servers
# Terminal 1 (Backend)
cd web/backend
npm run dev             # Starts on http://localhost:3001

# Terminal 2 (Frontend)
cd web/frontend
npm run dev             # Starts on http://localhost:5173
```

### Development Commands

```bash
# Backend
cd web/backend
npm run dev             # Development server (hot reload)
npm run build           # Production build
npm run start           # Production server
npm run lint            # ESLint
npm run format          # Prettier

# Frontend
cd web/frontend
npm run dev             # Development server (hot reload)
npm run build           # Production build
npm run preview         # Preview production build
npm run lint            # ESLint
npm run format          # Prettier
```

### Making Changes

#### Adding a New API Endpoint

1. Create route handler in `web/backend/src/routes/`
2. Add Zod validation schema
3. Add route to `index.ts`
4. Test with curl or Postman
5. Update frontend API client

**Example**:
```typescript
// routes/metrics.routes.ts
import { Router } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma';

const router = Router();

router.get('/metrics', async (req, res) => {
  const totalAnomalies = await prisma.anomaly.count();
  const validatedCount = await prisma.narrative.count({
    where: { validation_passed: true },
  });

  res.json({
    total_anomalies: totalAnomalies,
    validated_count: validatedCount,
    validation_rate: validatedCount / totalAnomalies,
  });
});

export default router;

// index.ts
import metricsRoutes from './routes/metrics.routes';
app.use('/api', metricsRoutes);
```

#### Adding a New Frontend Page

1. Create page component in `src/pages/`
2. Add route in `App.tsx`
3. Create necessary hooks in `src/hooks/`
4. Add to navigation

**Example**:
```typescript
// pages/MetricsDashboard.tsx
export function MetricsDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => api.getMetrics(),
  });

  if (isLoading) return <LoadingSkeleton />;

  return (
    <div>
      <h1>System Metrics</h1>
      <div>Total Anomalies: {data.total_anomalies}</div>
      <div>Validation Rate: {(data.validation_rate * 100).toFixed(1)}%</div>
    </div>
  );
}

// App.tsx
<Route path="/metrics" element={<MetricsDashboard />} />
```

## Deployment

### Production Build

```bash
# Backend
cd web/backend
npm run build           # Compiles TypeScript to dist/
npm run start           # Runs dist/index.js

# Frontend
cd web/frontend
npm run build           # Creates production build in dist/
# Serve dist/ with nginx or static hosting
```

### Docker Deployment

```dockerfile
# web/backend/Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npx prisma generate
RUN npm run build
CMD ["npm", "run", "start"]
EXPOSE 3001
```

```dockerfile
# web/frontend/Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: ./web/backend
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/mane_db
      JWT_SECRET: ${JWT_SECRET}
      NODE_ENV: production
    ports:
      - "3001:3001"
    depends_on:
      - postgres

  frontend:
    build: ./web/frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  postgres:
    image: postgres:14
    environment:
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Environment Variables (Production)

```bash
# web/backend/.env.production
DATABASE_URL="postgresql://user:pass@db-host:5432/mane_db?sslmode=require"
JWT_SECRET="strong-random-secret-change-this"
NODE_ENV="production"
CORS_ORIGIN="https://yourdomain.com"
```

### Nginx Configuration

```nginx
# nginx.conf (for frontend)
server {
  listen 80;
  server_name yourdomain.com;

  root /usr/share/nginx/html;
  index index.html;

  # Frontend SPA routing
  location / {
    try_files $uri $uri/ /index.html;
  }

  # Proxy API requests to backend
  location /api {
    proxy_pass http://backend:3001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
  }

  # Health check
  location /health {
    proxy_pass http://backend:3001;
  }
}
```

## Security

### Best Practices

1. **JWT Tokens**: httpOnly cookies prevent XSS attacks
2. **CORS**: Configured to allow only specific origins
3. **Rate Limiting**: Prevents brute force and DoS attacks
4. **Password Hashing**: bcrypt with salt rounds 10
5. **SQL Injection**: Prisma provides parameterized queries
6. **HTTPS**: Required in production (use Let's Encrypt)

### Security Headers

```typescript
// index.ts
import helmet from 'helmet';

app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  credentials: true,
}));
```

## Testing

### Backend Tests

```bash
cd web/backend
npm test               # Run all tests
npm run test:watch     # Watch mode
npm run test:coverage  # Coverage report
```

**Example Test**:
```typescript
// routes/auth.routes.test.ts
import request from 'supertest';
import { app } from '../index';

describe('POST /auth/login', () => {
  it('should return JWT token on valid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({ email: 'test@example.com', password: 'password123' });

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('user');
    expect(res.headers['set-cookie']).toBeDefined();
  });

  it('should return 401 on invalid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({ email: 'test@example.com', password: 'wrong' });

    expect(res.status).toBe(401);
  });
});
```

### Frontend Tests

```bash
cd web/frontend
npm test               # Run all tests
npm run test:watch     # Watch mode
npm run test:ui        # Vitest UI
```

**Example Test**:
```typescript
// components/AnomalyCard.test.tsx
import { render, screen } from '@testing-library/react';
import { AnomalyCard } from './AnomalyCard';

describe('AnomalyCard', () => {
  it('renders anomaly information', () => {
    const anomaly = {
      id: '123',
      symbol: 'BTC-USD',
      anomaly_type: 'price_drop',
      price_change_pct: -5.2,
      confidence: 0.89,
    };

    render(<AnomalyCard anomaly={anomaly} />);

    expect(screen.getByText('BTC-USD')).toBeInTheDocument();
    expect(screen.getByText('-5.2%')).toBeInTheDocument();
  });
});
```

## Troubleshooting

### Common Issues

**1. Prisma client not generated**
```bash
cd web/backend
npx prisma generate
```

**2. Port already in use**
```bash
# Kill process on port 3001
lsof -ti:3001 | xargs kill -9

# Or change port in .env
PORT=3002
```

**3. CORS errors**
```typescript
// Check CORS configuration in index.ts
app.use(cors({
  origin: 'http://localhost:5173',  // Must match frontend URL
  credentials: true,                 // Required for cookies
}));
```

**4. Database connection failed**
```bash
# Check DATABASE_URL in .env
# Ensure PostgreSQL is running
# Test connection:
psql "postgresql://user:pass@localhost:5432/mane_db"
```

**5. Frontend can't reach backend**
```typescript
// Check API_URL in frontend .env or lib/api.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';
```

## Performance Optimization

### Backend

1. **Database Indexing**: Prisma indexes on `symbol` and `detected_at`
2. **Query Optimization**: Use `include` instead of separate queries
3. **Caching**: Add Redis for frequently accessed data
4. **Connection Pooling**: Prisma handles this automatically

### Frontend

1. **Code Splitting**: Vite automatically splits by route
2. **Image Optimization**: Use WebP format
3. **Lazy Loading**: Lazy load chart components
4. **Memoization**: Use React.memo for expensive components

```typescript
// Lazy loading example
const ChartView = React.lazy(() => import('./pages/ChartView'));

<Suspense fallback={<LoadingSkeleton />}>
  <ChartView />
</Suspense>
```

## Monitoring

### Backend Logging

```typescript
// lib/logger.ts
import winston from 'winston';

export const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
  ],
});

// Usage
logger.info('User logged in', { userId: user.id });
logger.error('Database error', { error: err.message });
```

### Frontend Error Tracking

```typescript
// components/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Send to error tracking service (Sentry, etc.)
    console.error('Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong. Please refresh.</div>;
    }
    return this.props.children;
  }
}
```

---

**For more information**:
- Backend API Reference: `docs/API_REFERENCE.md`
- Database Schema: `docs/DATABASE.md`
- Development Workflow: `docs/DEVELOPMENT.md`
