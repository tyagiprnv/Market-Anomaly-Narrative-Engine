# Quick Start Guide - Web Application

Get the Market Anomaly Narrative Engine web app running in 5 minutes.

## Prerequisites

- Node.js 20+ installed (`node --version`)
- PostgreSQL database running (from Python pipeline setup)
- Python pipeline installed and database initialized

## Step 1: Database Migration

Add the users table to your existing database:

```bash
# From project root
psql -U mane_user -d mane_db -f web/backend/migrations/001_add_users_table.sql
```

If you get an error, connect manually:
```bash
psql -U mane_user -d mane_db
\i web/backend/migrations/001_add_users_table.sql
\q
```

## Step 2: Backend Setup

```bash
# Navigate to backend
cd web/backend

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Edit .env - IMPORTANT: Set these values
# DATABASE_URL=postgresql://mane_user:YOUR_PASSWORD@localhost:5432/mane_db
# JWT_SECRET=your-random-secret-at-least-32-characters

# Generate a secure JWT_SECRET (macOS/Linux):
openssl rand -base64 32

# Introspect database schema
npm run prisma:pull

# Generate Prisma client
npm run prisma:generate

# Start backend (runs on http://localhost:4000)
npm run dev
```

In a new terminal, verify backend is running:
```bash
curl http://localhost:4000/api/health
# Should return: {"status":"ok","timestamp":"...","service":"mane-backend","database":"connected"}
```

## Step 3: Frontend Setup

```bash
# Navigate to frontend (from project root)
cd web/frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Edit .env (default values should work)
# VITE_API_URL=http://localhost:4000/api

# Start frontend (runs on http://localhost:5173)
npm run dev
```

## Step 4: Test the Application

1. **Open browser:** http://localhost:5173
2. **Register an account:**
   - Click "Register" link
   - Enter email and password (min 8 chars)
   - Submit form
3. **Verify login:**
   - You should be redirected to dashboard
   - Check browser cookies for `token`
4. **Logout test:**
   - Open browser console
   - Run: `fetch('http://localhost:4000/api/auth/logout', {method: 'POST', credentials: 'include'})`
   - Refresh page - should redirect to login

## Step 5: Populate Data (Optional)

To see anomalies in the dashboard, run the Python detection pipeline:

```bash
# From project root (activate Python venv first)
source .venv/bin/activate

# Backfill historical price data (if not already done)
mane backfill --symbol BTC-USD --days 7

# Run detection once
mane detect --symbol BTC-USD --news-mode live

# Or start continuous monitoring
mane serve --news-mode live
```

## Troubleshooting

### Backend won't start

**Error:** `Environment validation failed: DATABASE_URL`
- Check your `.env` file has correct database credentials
- Verify PostgreSQL is running: `psql -U mane_user -d mane_db -c "SELECT 1;"`

**Error:** `Prisma Client validation failed`
- Run `npm run prisma:generate` again
- Delete `node_modules/.prisma` and regenerate

**Error:** `JWT_SECRET must be at least 32 characters`
- Generate a proper secret: `openssl rand -base64 32`
- Paste into `.env` file

### Frontend won't start

**Error:** `Cannot find module @mane/shared`
- Install shared dependencies: `cd ../shared && npm install`
- Link packages: `npm install` in frontend directory

**Error:** `Network Error` when testing login
- Verify backend is running: `curl http://localhost:4000/api/health`
- Check `VITE_API_URL` in frontend `.env` matches backend URL

### Can't login after registration

**Error:** `401 Unauthorized`
- Check backend logs for detailed error
- Verify users table was created: `psql -U mane_user -d mane_db -c "SELECT * FROM users;"`
- Check JWT_SECRET is the same value backend is using

### No anomalies showing up

- Dashboard is empty because no anomalies exist yet
- Run Python detection pipeline to populate data (see Step 5)
- Verify data in database: `psql -U mane_user -d mane_db -c "SELECT COUNT(*) FROM anomalies;"`

## Next Steps

Once the app is running:

1. **Explore the codebase:**
   - `web/backend/src/` - Express API implementation
   - `web/frontend/src/` - React UI components
   - `web/shared/` - Shared TypeScript types

2. **Read the documentation:**
   - [README.md](./README.md) - Complete feature documentation
   - [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) - Track development progress

3. **Start developing:**
   - Backend: `cd web/backend && npm run dev` (auto-reload on changes)
   - Frontend: `cd web/frontend && npm run dev` (hot module reload)
   - Run tests: `npm run test` in either directory

4. **Monitor the database:**
   - Open Prisma Studio: `cd web/backend && npm run prisma:studio`
   - View data at http://localhost:5555

## Development Workflow

```bash
# Terminal 1: Backend
cd web/backend
npm run dev

# Terminal 2: Frontend
cd web/frontend
npm run dev

# Terminal 3: Python pipeline (optional)
source .venv/bin/activate
mane serve --news-mode live

# Terminal 4: Watch tests (optional)
cd web/backend  # or web/frontend
npm run test:watch
```

## Common Commands

```bash
# Backend
cd web/backend
npm run dev              # Start dev server
npm run prisma:studio    # Open database GUI
npm run prisma:pull      # Re-sync schema from database
npm run test             # Run tests

# Frontend
cd web/frontend
npm run dev              # Start dev server
npm run build            # Production build
npm run preview          # Preview production build
npm run test             # Run tests

# Shared types
cd web/shared
npm run type-check       # Validate TypeScript
```

## Port Reference

- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:4000
- **Database:** localhost:5432
- **Prisma Studio:** http://localhost:5555 (when running)

## Support

If you encounter issues:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review backend logs in `web/backend/logs/`
3. Check browser console for frontend errors
4. Verify all services are running (backend, frontend, database)
