#!/bin/bash
# Test script for demo mode

echo "Testing Demo Mode Setup..."
echo ""

# Set demo mode
export DISABLE_DB=true

echo "✓ DISABLE_DB=true set"
echo ""

# Start the server in background
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 7860 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Test health endpoint
echo ""
echo "Testing /health endpoint..."
curl -s http://localhost:7860/health | python -m json.tool

# Test root endpoint
echo ""
echo "Testing / endpoint..."
curl -s http://localhost:7860/ | python -m json.tool

# Test dashboard escalations
echo ""
echo "Testing /dashboard/escalations endpoint..."
curl -s http://localhost:7860/dashboard/escalations | python -m json.tool

# Test support endpoint
echo ""
echo "Testing /support endpoint..."
curl -s -X POST http://localhost:7860/support \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","subject":"Test","message":"Testing demo mode"}' \
  | python -m json.tool

# Cleanup
echo ""
echo "Stopping server..."
kill $SERVER_PID

echo ""
echo "✓ Demo mode tests completed!"
