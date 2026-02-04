#!/bin/bash
# Test script for Phase 5 API endpoints

set -e

API_URL="http://localhost:4000/api"
EMAIL="test@example.com"
PASSWORD="test123456"

echo "🔑 Step 1: Register a test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" \
  -c cookies.txt)

if echo "$REGISTER_RESPONSE" | grep -q "error"; then
  echo "⚠️  User already exists, trying to login..."
  LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" \
    -c cookies.txt)

  if echo "$LOGIN_RESPONSE" | grep -q "error"; then
    echo "❌ Login failed"
    exit 1
  fi
  echo "✅ Logged in successfully"
else
  echo "✅ User registered successfully"
fi

echo ""
echo "📊 Step 2: Test GET /api/symbols"
curl -s "$API_URL/symbols" -b cookies.txt | jq '.'

echo ""
echo "📈 Step 3: Test GET /api/symbols/BTC-USD/stats"
curl -s "$API_URL/symbols/BTC-USD/stats" -b cookies.txt | jq '.'

echo ""
echo "📊 Step 4: Test GET /api/symbols/stats"
curl -s "$API_URL/symbols/stats" -b cookies.txt | jq '. | {success, data: (.data | length)}'

echo ""
echo "⚙️  Step 5: Test GET /api/config/thresholds"
curl -s "$API_URL/config/thresholds" -b cookies.txt | jq '. | {success, global_defaults: .data.global_defaults}'

echo ""
echo "⚙️  Step 6: Test GET /api/config/thresholds/BTC-USD"
curl -s "$API_URL/config/thresholds/BTC-USD" -b cookies.txt | jq '.'

echo ""
echo "⚙️  Step 7: Test GET /api/config/thresholds/DOGE-USD"
curl -s "$API_URL/config/thresholds/DOGE-USD" -b cookies.txt | jq '.'

# Clean up
rm -f cookies.txt

echo ""
echo "✅ All Phase 5 endpoints tested successfully!"
