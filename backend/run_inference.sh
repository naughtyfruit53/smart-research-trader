#!/bin/bash
# Convenience script to run inference and populate preds table

set -e

# Check if model path provided
if [ $# -eq 0 ]; then
    echo "Error: Model path required"
    echo "Usage: $0 <model_path> [options]"
    echo ""
    echo "Example:"
    echo "  $0 artifacts/models/model.txt"
    echo "  $0 artifacts/models/model.txt --date 2024-01-15"
    exit 1
fi

MODEL_PATH="$1"
shift

# Default parameters
TICKERS="${TICKERS:-RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS}"
HORIZON="${HORIZON:-1d}"

echo "=================================================="
echo "Running Inference"
echo "=================================================="
echo "Model: $MODEL_PATH"
echo "Tickers: $TICKERS"
echo "Horizon: $HORIZON"
echo "=================================================="

# Run inference
python -m src.ml.cli_inference \
    "$MODEL_PATH" \
    --tickers "$TICKERS" \
    --horizon "$HORIZON" \
    "$@"

echo ""
echo "=================================================="
echo "Inference complete!"
echo "Predictions saved to preds table"
echo "=================================================="
