"""LightGBM model wrapper with sensible defaults for time-series forecasting."""

import logging
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LGBMForecaster:
    """LightGBM regressor wrapper for return forecasting.

    Provides sensible defaults for time-series forecasting with early stopping
    and feature importance extraction.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = -1,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        random_state: int = 42,
        n_jobs: int = -1,
        verbose: int = -1,
        **kwargs: Any,
    ):
        """Initialize LightGBM forecaster.

        Args:
            n_estimators: Number of boosting rounds (default 100 for fast CI)
            learning_rate: Learning rate (default 0.05)
            num_leaves: Max number of leaves (default 31)
            max_depth: Max tree depth (-1 = no limit)
            min_child_samples: Minimum samples per leaf
            subsample: Subsample ratio of training data
            colsample_bytree: Subsample ratio of features
            reg_alpha: L1 regularization
            reg_lambda: L2 regularization
            random_state: Random seed
            n_jobs: Number of parallel jobs (-1 = use all cores)
            verbose: Verbosity level (-1 = silent)
            **kwargs: Additional LightGBM parameters
        """
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.min_child_samples = min_child_samples
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.verbose = verbose
        self.extra_params = kwargs

        self.model: lgb.Booster | None = None
        self.feature_names: list[str] = []
        self.best_iteration: int = 0

    def get_params(self) -> dict[str, Any]:
        """Get model parameters."""
        params = {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "min_child_samples": self.min_child_samples,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "verbose": self.verbose,
        }
        params.update(self.extra_params)
        return params

    def fit(
        self,
        X: pd.DataFrame | np.ndarray,
        y: pd.Series | np.ndarray,
        X_val: pd.DataFrame | np.ndarray | None = None,
        y_val: pd.Series | np.ndarray | None = None,
        early_stopping_rounds: int | None = 10,
        feature_names: list[str] | None = None,
    ) -> "LGBMForecaster":
        """Train LightGBM model.

        Args:
            X: Training features
            y: Training labels
            X_val: Optional validation features for early stopping
            y_val: Optional validation labels for early stopping
            early_stopping_rounds: Stop if no improvement for N rounds (None = no early stopping)
            feature_names: Optional feature names (inferred from DataFrame if not provided)

        Returns:
            Self (fitted model)
        """
        # Convert to numpy if needed
        if isinstance(X, pd.DataFrame):
            self.feature_names = feature_names or X.columns.tolist()
            X_train = X.values
        else:
            self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
            X_train = X

        if isinstance(y, pd.Series):
            y_train = y.values
        else:
            y_train = y

        # Create LightGBM dataset
        train_data = lgb.Dataset(
            X_train, label=y_train, feature_name=self.feature_names, free_raw_data=False
        )

        # Prepare validation set if provided
        valid_sets = [train_data]
        valid_names = ["train"]

        if X_val is not None and y_val is not None:
            if isinstance(X_val, pd.DataFrame):
                X_val_arr = X_val.values
            else:
                X_val_arr = X_val

            if isinstance(y_val, pd.Series):
                y_val_arr = y_val.values
            else:
                y_val_arr = y_val

            val_data = lgb.Dataset(
                X_val_arr,
                label=y_val_arr,
                reference=train_data,
                feature_name=self.feature_names,
                free_raw_data=False,
            )
            valid_sets.append(val_data)
            valid_names.append("valid")

        # Train model
        params = self.get_params()

        callbacks = []
        if early_stopping_rounds is not None and len(valid_sets) > 1:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )

        self.best_iteration = self.model.best_iteration

        logger.info(
            f"Trained LightGBM model: {self.best_iteration} iterations, "
            f"{len(self.feature_names)} features"
        )

        return self

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Make predictions.

        Args:
            X: Features

        Returns:
            Predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = X

        return self.model.predict(X_arr, num_iteration=self.best_iteration)

    def predict_with_std(
        self, X: pd.DataFrame | np.ndarray, n_trees: int = 50
    ) -> tuple[np.ndarray, np.ndarray]:
        """Make predictions with uncertainty estimates.

        Uses predictions from individual trees to estimate standard deviation.

        Args:
            X: Features
            n_trees: Number of trees to use for uncertainty estimation

        Returns:
            (predictions, standard_deviations)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = X

        # Get predictions from last n_trees
        n_trees_to_use = min(n_trees, self.best_iteration)
        tree_preds = []

        for i in range(max(1, self.best_iteration - n_trees_to_use), self.best_iteration + 1):
            pred = self.model.predict(X_arr, num_iteration=i)
            tree_preds.append(pred)

        tree_preds_arr = np.array(tree_preds)

        # Mean and std across trees
        yhat = tree_preds_arr.mean(axis=0)
        yhat_std = tree_preds_arr.std(axis=0)

        return yhat, yhat_std

    def get_feature_importance(self, importance_type: str = "gain") -> pd.DataFrame:
        """Get feature importances.

        Args:
            importance_type: Type of importance ('gain', 'split', or 'weight')

        Returns:
            DataFrame with columns [feature, importance]
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        importance = self.model.feature_importance(importance_type=importance_type)

        df = pd.DataFrame({"feature": self.feature_names, "importance": importance})

        return df.sort_values("importance", ascending=False)

    def save(self, path: str | Path) -> None:
        """Save model to file.

        Args:
            path: Path to save model
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        self.model.save_model(str(path))
        logger.info(f"Saved model to {path}")

    def load(self, path: str | Path) -> "LGBMForecaster":
        """Load model from file.

        Args:
            path: Path to load model from

        Returns:
            Self (loaded model)
        """
        self.model = lgb.Booster(model_file=str(path))
        self.best_iteration = self.model.best_iteration
        logger.info(f"Loaded model from {path}")
        return self
