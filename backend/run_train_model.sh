#!/bin/bash
# Convenience script to train ML model with walk-forward CV

set -e

# Default parameters
TICKERS="${TICKERS:-RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS}"
N_SPLITS="${N_SPLITS:-5}"
EMBARGO_DAYS="${EMBARGO_DAYS:-2}"
N_ESTIMATORS="${N_ESTIMATORS:-100}"
LEARNING_RATE="${LEARNING_RATE:-0.05}"
OUTPUT_DIR="${OUTPUT_DIR:-artifacts/models}"

echo "=================================================="
echo "Training LightGBM Model"
echo "=================================================="
echo "Tickers: $TICKERS"
echo "CV Splits: $N_SPLITS"
echo "Embargo: $EMBARGO_DAYS days"
echo "Estimators: $N_ESTIMATORS"
echo "Learning Rate: $LEARNING_RATE"
echo "Output: $OUTPUT_DIR"
echo "=================================================="

# Run training
python -m src.ml.cli_train \
    --tickers "$TICKERS" \
    --n-splits "$N_SPLITS" \
    --embargo-days "$EMBARGO_DAYS" \
    --n-estimators "$N_ESTIMATORS" \
    --learning-rate "$LEARNING_RATE" \
    --output-dir "$OUTPUT_DIR" \
    "$@"

echo ""
echo "=================================================="
echo "Training complete!"
echo "Metrics saved to: $OUTPUT_DIR/metrics.json"
echo "Feature importances: $OUTPUT_DIR/feature_importances.csv"
echo "=================================================="
