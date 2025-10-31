# ML Modeling Pipeline

This module provides a complete machine learning pipeline for forecasting next-day stock returns using LightGBM.

## Overview

The ML pipeline consists of:

1. **Labeling** (`labeling.py`): Compute forward 1-day returns from historical prices
2. **Time-Series CV** (`timesplit.py`): Expanding window cross-validation with embargo
3. **Model** (`model_lgbm.py`): LightGBM regressor wrapper with uncertainty estimation
4. **Training** (`train.py`): Walk-forward CV training pipeline
5. **Inference** (`inference.py`): Prediction generation and database population

## Quick Start

### 1. Prepare Labels

First, compute labels from historical prices and upsert to features table:

```python
from src.db.session import SessionLocal
from src.ml.labeling import compute_and_upsert_labels

db = SessionLocal()
num_updated = compute_and_upsert_labels(
    db, 
    tickers=["AAPL", "MSFT"],
    horizon_days=1
)
print(f"Updated {num_updated} feature rows with labels")
```

### 2. Train Model

Train a model with walk-forward cross-validation:

```bash
cd backend
python -m src.ml.cli_train \
    --tickers "AAPL,MSFT,GOOGL" \
    --n-splits 5 \
    --embargo-days 2 \
    --n-estimators 100 \
    --learning-rate 0.05 \
    --output-dir artifacts/models
```

This will:
- Train on features with labels using 5-fold expanding window CV
- Apply 2-day embargo between train and test sets
- Output metrics to `artifacts/models/metrics.json`
- Save feature importances to `artifacts/models/feature_importances.csv`

### 3. Run Inference

Generate predictions and populate the `preds` table:

```bash
python -m src.ml.cli_inference \
    artifacts/models/model.txt \
    --tickers "AAPL,MSFT,GOOGL" \
    --date 2024-01-15 \
    --horizon 1d
```

This will:
- Load the trained model
- Generate predictions for specified tickers and date
- Upsert predictions to `preds` table with columns: `yhat`, `yhat_std`, `prob_up`

## Python API

### Labeling

```python
from src.ml.labeling import compute_forward_returns

# Compute forward returns from prices DataFrame
labels = compute_forward_returns(
    prices_df,  # DataFrame with [ticker, dt, close]
    horizon_days=1
)
# Returns: DataFrame with [ticker, dt, label_ret_1d]
```

### Time-Series Cross-Validation

```python
from src.ml.timesplit import expanding_window_split

# Generate expanding window splits
splits = expanding_window_split(
    dates=df['dt'],
    n_splits=5,
    embargo_days=2,
    test_size=0.2,
    seed=42
)

for train_idx, test_idx in splits:
    # Use indices to split data
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
```

### Model Training

```python
from src.ml.model_lgbm import LGBMForecaster

# Create model with small defaults for fast training
model = LGBMForecaster(
    n_estimators=100,
    learning_rate=0.05,
    num_leaves=31
)

# Train with early stopping
model.fit(
    X_train, y_train,
    X_val=X_val, y_val=y_val,
    early_stopping_rounds=10
)

# Make predictions with uncertainty
yhat, yhat_std = model.predict_with_std(X_test)

# Get feature importance
importance_df = model.get_feature_importance()
```

### Full Training Pipeline

```python
from src.ml.train import train_with_walk_forward_cv

results = train_with_walk_forward_cv(
    db=db,
    tickers=["AAPL", "MSFT"],
    n_splits=5,
    embargo_days=2,
    model_params={"n_estimators": 100, "learning_rate": 0.05},
    output_dir="artifacts/models"
)

print(f"Mean RMSE: {results['overall_metrics']['rmse_mean']:.4f}")
print(f"Mean R2: {results['overall_metrics']['r2_mean']:.4f}")
```

### Inference

```python
from src.ml.inference import run_inference

num_preds = run_inference(
    db=db,
    model_path="artifacts/models/model.txt",
    tickers=["AAPL", "MSFT"],
    target_date=date(2024, 1, 15),
    horizon="1d"
)

print(f"Generated {num_preds} predictions")
```

## CLI Reference

### Training CLI

```bash
python -m src.ml.cli_train [OPTIONS]

Options:
  --tickers TEXT              Comma-separated tickers (default: from env)
  --start-date YYYY-MM-DD     Start date for training data
  --end-date YYYY-MM-DD       End date for training data
  --n-splits INT              Number of CV folds (default: 5)
  --embargo-days INT          Embargo days between train/test (default: 2)
  --test-size FLOAT           Test set fraction (default: 0.2)
  --n-estimators INT          Number of boosting rounds (default: 100)
  --learning-rate FLOAT       Learning rate (default: 0.05)
  --num-leaves INT            Max leaves per tree (default: 31)
  --output-dir PATH           Output directory (default: artifacts/models)
  --seed INT                  Random seed (default: 42)
  --no-importances           Don't save feature importances
```

### Inference CLI

```bash
python -m src.ml.cli_inference MODEL_PATH [OPTIONS]

Positional Arguments:
  MODEL_PATH                  Path to trained model file

Options:
  --tickers TEXT              Comma-separated tickers (default: from env)
  --date YYYY-MM-DD           Target date for predictions (default: latest)
  --horizon TEXT              Prediction horizon label (default: 1d)
```

## Predictions Schema

Predictions are stored in the `preds` table with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| ticker | TEXT | Stock ticker symbol |
| dt | DATE | Date of the prediction |
| horizon | TEXT | Prediction horizon (e.g., "1d") |
| yhat | FLOAT | Predicted return |
| yhat_std | FLOAT | Standard deviation of prediction |
| prob_up | FLOAT | Probability of positive return (0-1) |

Primary key: `(ticker, dt, horizon)`

## Metrics

The training pipeline outputs several metrics:

- **RMSE**: Root Mean Squared Error
- **MAE**: Mean Absolute Error
- **R2**: R-squared score
- **Direction Accuracy**: % of times sign is predicted correctly

Metrics are computed per-fold and aggregated (mean ± std).

## Model Configuration

Default model parameters (optimized for fast CI):

```python
{
    "n_estimators": 100,          # Number of trees
    "learning_rate": 0.05,        # Shrinkage
    "num_leaves": 31,             # Max leaves per tree
    "max_depth": -1,              # No depth limit
    "min_child_samples": 20,      # Min samples per leaf
    "subsample": 0.8,             # Row sampling
    "colsample_bytree": 0.8,      # Feature sampling
    "reg_alpha": 0.1,             # L1 regularization
    "reg_lambda": 0.1,            # L2 regularization
}
```

These defaults prioritize:
- Fast training (100 estimators)
- Robustness (regularization, subsampling)
- Reasonable complexity (31 leaves)

## Best Practices

### Data Requirements

- Minimum 50-100 samples per ticker for reliable training
- At least 10 non-null features per sample
- Labels should be computed from actual forward returns

### Cross-Validation

- Use **embargo_days ≥ 2** to prevent leakage
- Use **n_splits = 5** for balance between computation and robustness
- Use **test_size = 0.2** (20% of data per fold)

### Model Tuning

Start with defaults, then tune in this order:
1. `n_estimators` (try 50, 100, 200)
2. `learning_rate` (try 0.01, 0.05, 0.1)
3. `num_leaves` (try 15, 31, 63)
4. Regularization (`reg_alpha`, `reg_lambda`)

### Production Deployment

1. Train on all available data
2. Save model with `model.save(path)`
3. Run daily inference after features are updated
4. Monitor prediction quality over time

## Troubleshooting

### Issue: No features with labels found

**Solution**: Run labeling first:
```python
from src.ml.labeling import compute_and_upsert_labels
compute_and_upsert_labels(db, tickers=["AAPL"])
```

### Issue: Not enough samples for N splits

**Solution**: Reduce `n_splits` or increase date range:
```bash
python -m src.ml.cli_train --n-splits 3 --start-date 2020-01-01
```

### Issue: Model overfitting (high train, low test performance)

**Solution**: Increase regularization:
```bash
python -m src.ml.cli_train --n-estimators 50 --learning-rate 0.01
```

## Testing

Run ML tests:

```bash
cd backend
pytest tests/test_ml*.py -v
```

Tests cover:
- Labeling logic and database operations
- Time-series CV split generation
- Model training and prediction
- Inference pipeline
- CLI argument parsing

## Architecture

```
backend/src/ml/
├── __init__.py              # Module init
├── labeling.py              # Forward return computation
├── timesplit.py             # Time-series CV splits
├── model_lgbm.py            # LightGBM wrapper
├── train.py                 # Training pipeline
├── inference.py             # Inference pipeline
├── cli_train.py             # Training CLI
└── cli_inference.py         # Inference CLI

backend/tests/
├── test_ml_labeling.py      # Labeling tests
├── test_ml_timesplit.py     # CV split tests
├── test_ml_model_lgbm.py    # Model tests
├── test_ml_train.py         # Training tests
└── test_ml_inference.py     # Inference tests

backend/artifacts/models/
├── metrics.json             # Training metrics (output)
├── feature_importances.csv  # Feature importances (output)
└── model.txt                # Trained model (manual save)
```

## Future Enhancements

- [ ] Multi-horizon forecasting (1d, 5d, 20d)
- [ ] Ensemble models (LightGBM + XGBoost + CatBoost)
- [ ] Online learning (incremental updates)
- [ ] Hyperparameter optimization (Optuna)
- [ ] Model versioning and experiment tracking (MLflow)
- [ ] Prediction explanations (SHAP values)
- [ ] Automated retraining pipeline
- [ ] A/B testing framework

## References

- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [Time-Series Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
- [Financial ML (Marcos López de Prado)](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086)
