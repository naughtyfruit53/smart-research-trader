#!/bin/bash
set -e  # Exit on error

# ==============================================================================
# Seed Demo Script - Orchestrate end-to-end data population for demo
# ==============================================================================
# This script runs the full pipeline to populate data for demo purposes:
# 1. Fetch historical prices (yfinance)
# 2. Import fundamentals (from CSV if provided)
# 3. Fetch news (optional, RSS-based)
# 4. Compute features (technicals, fundamentals, sentiment)
# 5. Compute labels (forward returns)
# 6. Train ML model
# 7. Run inference for latest date
# 8. Run backtest
#
# Usage:
#   ./infra/scripts/seed_demo.sh [FUNDAMENTALS_CSV_PATH]
#
# Environment variables (with defaults):
#   DATABASE_URL - PostgreSQL connection string
#   TICKERS - Comma-separated list of tickers (default: NIFTY large caps)
#   PRICE_PROVIDER - yf or nse (default: yf)
#   ENABLE_FINBERT - false (to speed up demo)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../../backend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default demo tickers (NIFTY large caps)
DEFAULT_TICKERS="RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS,HINDUNILVR.NS,ITC.NS,SBIN.NS,BHARTIARTL.NS,KOTAKBANK.NS"

# Export environment variables for backend scripts
export DATABASE_URL="${DATABASE_URL:-postgresql://trader:trader_dev_pass@localhost:5432/smart_trader}"
export TICKERS="${TICKERS:-$DEFAULT_TICKERS}"
export PRICE_PROVIDER="${PRICE_PROVIDER:-yf}"
export ENABLE_FINBERT="${ENABLE_FINBERT:-false}"
export NEWS_PROVIDER="${NEWS_PROVIDER:-rss}"

FUNDAMENTALS_CSV="${1:-}"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Smart Research Trader - Seed Demo${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Configuration:"
echo "  Database: $DATABASE_URL"
echo "  Tickers: $TICKERS"
echo "  Price Provider: $PRICE_PROVIDER"
echo "  Enable FinBERT: $ENABLE_FINBERT"
echo "  Fundamentals CSV: ${FUNDAMENTALS_CSV:-None}"
echo ""

# Change to backend directory
cd "$BACKEND_DIR"

# Check if we're in a virtual environment or can use python3
if [ -z "$VIRTUAL_ENV" ]; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# ==============================================================================
# Step 1: Fetch Prices
# ==============================================================================
echo -e "${YELLOW}[1/8] Fetching historical prices...${NC}"
if $PYTHON_CMD -m src.data.etl.fetch_prices --tickers "$TICKERS"; then
    echo -e "${GREEN}✓ Prices fetched successfully${NC}"
else
    echo -e "${RED}✗ Failed to fetch prices${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 2: Import Fundamentals (if CSV provided)
# ==============================================================================
if [ -n "$FUNDAMENTALS_CSV" ] && [ -f "$FUNDAMENTALS_CSV" ]; then
    echo -e "${YELLOW}[2/8] Importing fundamentals from CSV...${NC}"
    if $PYTHON_CMD -m src.data.etl.fetch_fundamentals --csv-path "$FUNDAMENTALS_CSV"; then
        echo -e "${GREEN}✓ Fundamentals imported successfully${NC}"
    else
        echo -e "${RED}✗ Failed to import fundamentals${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[2/8] Skipping fundamentals import (no CSV provided)${NC}"
    echo "  To import fundamentals, provide a CSV path as first argument"
fi
echo ""

# ==============================================================================
# Step 3: Fetch News (optional)
# ==============================================================================
echo -e "${YELLOW}[3/8] Fetching news articles...${NC}"
if $PYTHON_CMD -m src.data.etl.fetch_news --tickers "$TICKERS" --days 90; then
    echo -e "${GREEN}✓ News fetched successfully${NC}"
else
    echo -e "${YELLOW}⚠ News fetch had warnings (continuing)${NC}"
fi
echo ""

# ==============================================================================
# Step 4: Compute Features
# ==============================================================================
echo -e "${YELLOW}[4/8] Computing features (technicals, fundamentals, sentiment)...${NC}"
if $PYTHON_CMD -m src.data.etl.compute_features --tickers "$TICKERS"; then
    echo -e "${GREEN}✓ Features computed successfully${NC}"
else
    echo -e "${RED}✗ Failed to compute features${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 5: Compute Labels
# ==============================================================================
echo -e "${YELLOW}[5/8] Computing labels (forward returns)...${NC}"
if $PYTHON_CMD -m src.ml.cli_label --tickers "$TICKERS" --horizon-days 1; then
    echo -e "${GREEN}✓ Labels computed successfully${NC}"
else
    echo -e "${RED}✗ Failed to compute labels${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 6: Train Model
# ==============================================================================
echo -e "${YELLOW}[6/8] Training ML model...${NC}"
MODEL_PATH="models/lgbm_1d_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p models
if $PYTHON_CMD -m src.ml.cli_train --tickers "$TICKERS" --n-splits 3 --output "$MODEL_PATH"; then
    echo -e "${GREEN}✓ Model trained successfully: $MODEL_PATH${NC}"
else
    echo -e "${RED}✗ Failed to train model${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 7: Run Inference (for latest date)
# ==============================================================================
echo -e "${YELLOW}[7/8] Running inference for latest date...${NC}"
if $PYTHON_CMD -m src.ml.cli_inference "$MODEL_PATH" --tickers "$TICKERS" --horizon "1d"; then
    echo -e "${GREEN}✓ Inference completed successfully${NC}"
else
    echo -e "${RED}✗ Failed to run inference${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Step 8: Run Backtest
# ==============================================================================
echo -e "${YELLOW}[8/8] Running backtest...${NC}"
# Create a simple Python script to run backtest
$PYTHON_CMD << EOF
from src.db.session import SessionLocal
from src.ml.backtest import run_backtest

db = SessionLocal()
try:
    run_id = run_backtest(
        db,
        start_date=None,  # Use all available data
        end_date=None,
        long_threshold=0.5,
        short_threshold=-0.5,
        transaction_cost_bps=10.0,
        max_long=20,
        max_short=10,
        max_gross=30,
        rebalance_daily=True,
    )
    print(f"✓ Backtest completed with run_id: {run_id}")
except Exception as e:
    print(f"✗ Backtest failed: {e}")
    raise
finally:
    db.close()
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backtest completed successfully${NC}"
else
    echo -e "${RED}✗ Failed to run backtest${NC}"
    exit 1
fi
echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Seed Demo Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the services: docker compose up"
echo "  2. Open the frontend: http://localhost:5173"
echo "  3. View signals: http://localhost:5173/signals"
echo "  4. View backtests: http://localhost:5173/backtests"
echo "  5. API docs: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}⚠ This is a demo with limited data. For production use:${NC}"
echo "  - Add more tickers and longer history"
echo "  - Tune model hyperparameters"
echo "  - Enable FinBERT for better sentiment"
echo "  - Add proper fundamentals data"
echo ""
echo -e "${GREEN}Happy trading! (Research purposes only)${NC}"
