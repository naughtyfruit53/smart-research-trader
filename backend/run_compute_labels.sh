#!/bin/bash
# Convenience script to compute forward return labels

set -e

# Default parameters
TICKERS="${TICKERS:-RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS}"
HORIZON_DAYS="${HORIZON_DAYS:-1}"

echo "=================================================="
echo "Computing Forward Return Labels"
echo "=================================================="
echo "Tickers: $TICKERS"
echo "Horizon: $HORIZON_DAYS day(s)"
echo "=================================================="

# Run labeling
python -m src.ml.cli_label \
    --tickers "$TICKERS" \
    --horizon-days "$HORIZON_DAYS" \
    "$@"

echo ""
echo "=================================================="
echo "Labeling complete!"
echo "Labels saved to features.label_ret_${HORIZON_DAYS}d"
echo "=================================================="
