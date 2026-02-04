# Web Application Verification Checklist

Use this checklist to verify the web application is set up correctly.

## ✅ Phase 1: File Structure Verification

Run from project root:

```bash
cd web

# Verify all key files exist
ls -la shared/package.json
ls -la backend/package.json
ls -la frontend/package.json
ls -la backend/src/index.ts
ls -la frontend/src/main.tsx
ls -la shared/types/database.ts
ls -la backend/migrations/001_add_users_table.sql
```

Expected output: All files should exist without errors.

---

## ✅ Phase 2: Database Migration

### Step 1: Verify PostgreSQL is running

```bash
psql -U mane_user -d mane_db -c "SELECT version();"
```

Expected: PostgreSQL version info

### Step 2: Run users table migration

```bash
psql -U mane_user -d mane_db -f web/backend/migrations/001_add_users_table.sql
```

Expected output:
```
CREATE TABLE
CREATE INDEX
CREATE FUNCTION
CREATE TRIGGER
```

### Step 3: Verify users table exists

```bash
psql -U mane_user -d mane_db -c "\d users"
```

Expected: Table definition with columns (id, email, password_hash, created_at, updated_at)

---

## ✅ Phase 3: Backend Setup

### Step 1: Install dependencies

```bash
cd web/backend
npm install
```

Expected: Should complete without errors. Check for ~26 packages installed.

### Step 2: Create .env file

```bash
cp .env.example .env
```

Edit `.env` and set:
- `DATABASE_URL` (from your existing Python setup)
- `JWT_SECRET` (generate with `openssl rand -base64 32`)

Verify your .env:
```bash
cat .env | grep -E "DATABASE_URL|JWT_SECRET"
```

### Step 3: Introspect database schema

```bash
npm run prisma:pull
```

Expected output:
```
✔ Introspected 5 models and wrote them into prisma/schema.prisma
```

Verify schema was created:
```bash
ls -la prisma/schema.prisma
```

### Step 4: Generate Prisma client

```bash
npm run prisma:generate
```

Expected output:
```
✔ Generated Prisma Client
```

### Step 5: Type check

```bash
npm run type-check
```

Expected: No TypeScript errors

### Step 6: Start backend server

```bash
npm run dev
```

Expected output:
```
🚀 Server running on http://localhost:4000
📊 Environment: development
🔗 CORS enabled for: http://localhost:5173
```

Keep this terminal running!

---

## ✅ Phase 4: Backend API Testing

Open a new terminal:

### Test 1: Health check

```bash
curl http://localhost:4000/api/health
```

Expected:
```json
{
  "status": "ok",
  "timestamp": "...",
  "service": "mane-backend",
  "database": "connected"
}
```

### Test 2: Register user

```bash
curl -X POST http://localhost:4000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt
```

Expected: HTTP 201 with user object

### Test 3: Login

```bash
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt
```

Expected: HTTP 200 with user object and token cookie

### Test 4: Get current user (authenticated)

```bash
curl http://localhost:4000/api/auth/me -b cookies.txt
```

Expected: User object with email

### Test 5: Logout

```bash
curl -X POST http://localhost:4000/api/auth/logout -b cookies.txt
```

Expected: Success message

### Test 6: Access protected route (should fail after logout)

```bash
curl http://localhost:4000/api/auth/me -b cookies.txt
```

Expected: HTTP 401 Unauthorized

---

## ✅ Phase 5: Frontend Setup

### Step 1: Install dependencies

```bash
cd web/frontend
npm install
```

Expected: Should complete without errors. Check for ~25 packages installed.

### Step 2: Create .env file

```bash
cp .env.example .env
```

Verify (default values should work):
```bash
cat .env
```

Expected:
```
VITE_API_URL=http://localhost:4000/api
```

### Step 3: Type check

```bash
npm run type-check
```

Expected: No TypeScript errors

### Step 4: Start frontend server

```bash
npm run dev
```

Expected output:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Keep this terminal running!

---

## ✅ Phase 6: Frontend UI Testing

### Test 1: Open browser

Visit: http://localhost:5173

Expected: Login page displayed

### Test 2: Registration flow

1. Click "Don't have an account? Register"
2. Enter email: `your@email.com`
3. Enter password: `password123` (min 8 chars)
4. Click "Register"

Expected:
- Redirected to dashboard
- URL changes to http://localhost:5173/
- Dashboard shows "Dashboard" heading

### Test 3: Verify authentication state

Open browser DevTools:
- **Application → Cookies**
  - Should see `token` cookie
  - `HttpOnly` flag should be checked
  - `SameSite` should be "Strict"

### Test 4: Logout via console

In browser console:
```javascript
fetch('http://localhost:4000/api/auth/logout', {
  method: 'POST',
  credentials: 'include'
})
```

Refresh page → should redirect to login

### Test 5: Login flow

1. Enter email and password
2. Click "Sign in"
3. Should redirect to dashboard

### Test 6: Protected route

While logged in, try accessing `/login` directly:
- Should redirect to `/` (dashboard)

### Test 7: Check browser console

- No errors in console
- React Query devtools should be available (bottom-left icon)

---

## ✅ Phase 7: Shared Types Verification

### Test 1: Type imports in backend

```bash
cd web/backend
grep -r "@mane/shared" src/
```

Expected: Should find imports in service/controller files (when implemented)

### Test 2: Type imports in frontend

```bash
cd web/frontend
grep -r "@mane/shared" src/
```

Expected: Should find imports in context, utils, etc.

---

## ✅ Phase 8: Development Workflow

### Test 1: Backend hot reload

1. Keep backend server running
2. Edit `web/backend/src/routes/health.routes.ts`
3. Add a comment
4. Server should auto-restart

Expected output:
```
[nodemon] restarting due to changes...
[nodemon] starting `tsx src/index.ts`
```

### Test 2: Frontend hot reload

1. Keep frontend server running
2. Edit `web/frontend/src/App.tsx`
3. Change "Dashboard" text to "Dashboard Test"
4. Browser should auto-update

Expected: Text changes immediately without refresh

---

## ✅ Phase 9: Database Verification

### Test 1: Verify user was created

```bash
psql -U mane_user -d mane_db -c "SELECT id, email, created_at FROM users;"
```

Expected: Your registered user(s) should appear

### Test 2: Open Prisma Studio

```bash
cd web/backend
npm run prisma:studio
```

Expected:
- Browser opens to http://localhost:5555
- Can view `users` table
- Can view `anomalies`, `prices`, etc.

---

## ✅ Phase 10: Error Handling

### Test 1: Invalid credentials

```bash
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrongpassword"}'
```

Expected: HTTP 401 with error message

### Test 2: Duplicate registration

Try registering with same email twice in UI.

Expected: Error toast notification

### Test 3: Missing JWT

```bash
curl http://localhost:4000/api/auth/me
```

Expected: HTTP 401 Unauthorized

### Test 4: Rate limiting

Run this command 6 times quickly:

```bash
curl -X POST http://localhost:4000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrongpassword"}'
```

Expected: After 5 attempts, should get HTTP 429 (Too Many Requests)

---

## ✅ Phase 11: Logs Verification

### Test 1: Check backend logs

```bash
cd web/backend
cat logs/combined.log | tail -20
```

Expected: Recent log entries (requests, responses, errors)

### Test 2: Check error logs

```bash
cat logs/error.log
```

Expected: Only errors (if any occurred during testing)

---

## ✅ Phase 12: TypeScript Strict Mode

### Test 1: Shared types

```bash
cd web/shared
npm run type-check
```

Expected: No errors

### Test 2: Backend types

```bash
cd web/backend
npm run type-check
```

Expected: No errors

### Test 3: Frontend types

```bash
cd web/frontend
npm run type-check
```

Expected: No errors

---

## ✅ Phase 13: Environment Validation

### Test 1: Missing JWT_SECRET

```bash
cd web/backend
# Temporarily rename .env
mv .env .env.backup
npm run dev
```

Expected: Error message about missing JWT_SECRET

Restore:
```bash
mv .env.backup .env
```

### Test 2: Invalid DATABASE_URL

Edit `.env` and set invalid URL:
```
DATABASE_URL=invalid-url
```

Run:
```bash
npm run dev
```

Expected: Zod validation error

Fix by restoring correct URL.

---

## ✅ Common Issues & Fixes

### Issue: Backend won't start - "Prisma Client validation failed"

**Fix:**
```bash
cd web/backend
rm -rf node_modules/.prisma
npm run prisma:generate
```

### Issue: Frontend can't reach backend - "Network Error"

**Fix:**
1. Verify backend is running: `curl http://localhost:4000/api/health`
2. Check CORS: Verify `FRONTEND_URL` in backend `.env` matches frontend URL
3. Check proxy in `vite.config.ts`

### Issue: "Cannot find module @mane/shared"

**Fix:**
```bash
cd web/shared
npm install
cd ../backend  # or ../frontend
npm install
```

### Issue: Database connection error

**Fix:**
1. Verify PostgreSQL is running: `psql -U mane_user -d mane_db`
2. Check `DATABASE_URL` in `.env`
3. Verify credentials match Python pipeline setup

### Issue: JWT verification fails

**Fix:**
1. Ensure `JWT_SECRET` is set in backend `.env`
2. Ensure it's at least 32 characters
3. Clear browser cookies and re-login

---

## ✅ Success Criteria

All checks passed when:

- ✅ Backend starts without errors
- ✅ Frontend starts without errors
- ✅ Health endpoint returns "ok"
- ✅ User registration works
- ✅ User login works
- ✅ JWT authentication works (protected routes)
- ✅ Logout works
- ✅ Database connection works
- ✅ Prisma introspection works
- ✅ TypeScript compilation succeeds (no errors)
- ✅ Hot reload works for both frontend and backend
- ✅ Rate limiting works
- ✅ Error handling works
- ✅ Logs are being written

---

## Next Steps After Verification

Once all checks pass:

1. **Read the documentation:**
   - `web/README.md` - Full feature docs
   - `web/QUICKSTART.md` - Setup guide
   - `web/IMPLEMENTATION_STATUS.md` - Progress tracker
   - `WEB_APP_SUMMARY.md` - High-level overview

2. **Start development:**
   - Implement anomaly API endpoints (Phase 3)
   - Build dashboard UI (Phase 6)
   - Add charts (Phase 8)

3. **Populate test data:**
   - Run Python detection pipeline to create anomalies
   - Verify data appears in Prisma Studio

4. **Monitor logs:**
   - Terminal 1: Backend dev server
   - Terminal 2: Frontend dev server
   - Terminal 3: Python pipeline (optional)
   - Terminal 4: Logs tail: `tail -f web/backend/logs/combined.log`

---

## Support

If you encounter issues not covered here:

1. Check terminal output for error messages
2. Check browser console for frontend errors
3. Check `web/backend/logs/error.log` for backend errors
4. Review `web/README.md` troubleshooting section
5. Verify all environment variables are set correctly
6. Ensure PostgreSQL is running and accessible
