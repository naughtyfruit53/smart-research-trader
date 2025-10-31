#!/bin/bash

set -e

echo "🚀 Starting Smart Research Trader development environment..."
echo ""

# Change to repo root
cd "$(dirname "$0")/../.."

# Start services
docker compose up --build

echo ""
echo "✅ Services started!"
echo ""
echo "📍 Endpoints:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend:  http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
