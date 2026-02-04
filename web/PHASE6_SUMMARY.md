# Phase 6: Dashboard Page - Implementation Summary

## Completed Features

### 1. Query Hooks (`src/api/queries/anomalies.ts`)
- **useAnomalies**: Fetch paginated anomalies with filters (symbol, type, validation, dates)
- **useLatestAnomalies**: Live polling (30s) for real-time updates with `since` parameter
- **useAnomaly**: Fetch single anomaly by ID (for detail view)
- **useAnomalyStats**: Fetch aggregated statistics (total count, by type, by validation, avg confidence)

### 2. Dashboard Components

#### AnomalyCard (`src/components/dashboard/AnomalyCard.tsx`)
- Color-coded by anomaly type (spike=green, drop=red, volume=yellow, combined=blue)
- Displays key metrics: price, return %, Z-score, confidence
- Shows narrative text (if available) with line-clamp
- Validation status badge
- Detection metadata (timeframe windows from multi-timeframe detector)
- Relative and absolute timestamps
- Click handler for navigation to detail view

#### AnomalyList (`src/components/dashboard/AnomalyList.tsx`)
- Responsive grid layout (1/2/3 columns based on screen size)
- Empty state with icon and custom message
- Maps over anomalies and renders AnomalyCard components

#### SymbolSelector (`src/components/dashboard/SymbolSelector.tsx`)
- Multi-select dropdown with checkboxes
- "Select All" and "Clear All" buttons
- Shows symbol ticker + full name (e.g., "BTC - Bitcoin")
- Outside-click handler to close dropdown
- Dynamic display text ("All Symbols", "BTC", "3 symbols")
- Scrollable list for 20+ symbols

#### LiveIndicator (`src/components/dashboard/LiveIndicator.tsx`)
- Green pulsing dot when polling is active
- Gray dot when paused/loading
- Shows last update time (e.g., "Updated 30 seconds ago")
- Real-time status: "Live" or "Paused"

### 3. Layout Component

#### AppLayout (`src/components/layout/AppLayout.tsx`)
- Header with logo, app title, user email, logout button
- Max-width container (7xl) with responsive padding
- Consistent layout for all authenticated pages

### 4. Dashboard Page (`src/pages/Dashboard.tsx`)
- Live feed with 30-second auto-refresh
- Symbol filter (multi-select)
- Summary stats (total anomalies, avg confidence)
- Loading states with spinner
- Empty states with contextual messages
- Click on anomaly card → navigate to `/anomalies/:id`

### 5. Routing Updates (`src/App.tsx`)
- `/` → Dashboard (protected)
- `/anomalies/:id` → Anomaly Detail (placeholder for Phase 7)
- `/login`, `/register` → Auth pages
- Catch-all redirect to `/`

---

## File Structure

```
web/frontend/src/
├── api/queries/
│   ├── anomalies.ts     # React Query hooks
│   └── index.ts         # Barrel export
├── components/
│   ├── dashboard/
│   │   ├── AnomalyCard.tsx
│   │   ├── AnomalyList.tsx
│   │   ├── SymbolSelector.tsx
│   │   ├── LiveIndicator.tsx
│   │   └── index.ts
│   └── layout/
│       └── AppLayout.tsx
├── pages/
│   └── Dashboard.tsx
└── App.tsx              # Updated routes
```

---

## Testing Instructions

### Prerequisites
1. Backend must be running with database populated
2. User account registered (or use existing)

### Start the Application

```bash
# Terminal 1: Backend
cd web/backend
npm run dev

# Terminal 2: Frontend
cd web/frontend
npm run dev
```

### Test Scenarios

#### 1. Login and View Dashboard
1. Navigate to http://localhost:5173
2. Log in with credentials
3. Should redirect to dashboard showing live anomalies

#### 2. Symbol Filtering
1. Click "All Symbols" dropdown
2. Select "BTC-USD" only
3. Click outside to close
4. Dashboard should show only BTC anomalies
5. Click dropdown again, select "ETH-USD" too
6. Should show "2 symbols" in button
7. Click "Clear All" → should show all symbols

#### 3. Live Polling
1. Watch the "Live" indicator (green pulsing dot)
2. After 30 seconds, the query should auto-refetch
3. "Updated X seconds ago" should update
4. Check browser network tab → should see `/api/anomalies/latest` calls every 30s

#### 4. Empty States
1. Select a symbol with no anomalies (e.g., a newly added one)
2. Should see "No anomalies found for selected symbols"
3. Click "Clear All" on symbol filter
4. If no data: "No anomalies detected yet. The system is monitoring markets..."

#### 5. Anomaly Card Click
1. Click on any anomaly card
2. Should navigate to `/anomalies/{id}`
3. Should see placeholder page "Anomaly Detail (Phase 7)"

#### 6. Statistics Display
1. Check top stats bar shows:
   - Total Anomalies count
   - Average Confidence percentage
2. Change symbol filter → stats should update

---

## Expected Behavior

### Query Caching
- Latest anomalies: fresh fetch every 30s (staleTime: 0, refetchInterval: 30s)
- Anomaly stats: cached for 1 minute (staleTime: 60s)
- Single anomaly: cached for 1 minute (staleTime: 60s)

### Performance
- Grid layout renders 20+ cards efficiently
- Dropdown scrollable for 20+ symbols
- React Query prevents duplicate requests

### Accessibility
- Semantic HTML (header, main, buttons, labels)
- Focus states on interactive elements
- Keyboard navigation for dropdown (checkboxes)
- Screen reader friendly labels

---

## Known Limitations (To Be Addressed)

1. **No error handling UI** - errors only logged to console (Phase 10)
2. **No loading skeletons** - just spinner (Phase 10)
3. **No toast notifications** - no feedback for actions (Phase 10)
4. **Detail view is placeholder** - implement in Phase 7
5. **No date range filtering** - dashboard only shows latest (Historical Browser in Phase 9)
6. **No pagination controls** - only latest 100 anomalies shown

---

## Next Steps: Phase 7 - Anomaly Detail View

Implement the detail page at `/anomalies/:id`:
- Full anomaly metrics panel
- Narrative display with source attribution
- Validation status with reasoning
- News clusters with articles
- Sentiment and timing indicators
- Related news articles list
- Link to price chart view

---

## Color Legend

### Anomaly Types
- **Price Spike**: Green (success)
- **Price Drop**: Red (danger)
- **Volume Spike**: Yellow (warning)
- **Combined**: Blue (info)

### Validation Status
- **VALID**: Green
- **INVALID**: Red
- **UNVALIDATED**: Gray

### News Sentiment
- **POSITIVE**: Green
- **NEGATIVE**: Red
- **NEUTRAL**: Gray

---

## API Endpoints Used

- `GET /api/anomalies/latest?since={timestamp}&symbol={symbol}`
- `GET /api/anomalies/stats?symbol={symbol}`
- `GET /api/anomalies/{id}` (Phase 7)

All endpoints require authentication (JWT in httpOnly cookie).
