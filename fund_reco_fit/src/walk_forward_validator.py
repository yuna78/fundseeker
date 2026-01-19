"""
Walk-Forward Validation System for Fund Selection Models

This module implements a time-series cross-validation framework that:
1. Splits data into rolling train/test windows
2. Trains models on each window
3. Evaluates on out-of-sample periods
4. Compares predictions with actual 2025 performance
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ValidationWindow:
    """Represents a single train/test split in walk-forward validation."""

    train_start: str
    train_end: str
    test_start: str
    test_end: str
    window_id: int

    def __str__(self) -> str:
        return f"Window {self.window_id}: Train[{self.train_start} to {self.train_end}] → Test[{self.test_start} to {self.test_end}]"


@dataclass
class ValidationResult:
    """Results from a single validation window."""

    window: ValidationWindow
    hit_rate: float
    hit_count: int
    total_predictions: int
    sharpe_ratio: float
    annual_return: float
    max_drawdown: float
    weights: Dict[str, float]
    predicted_funds: List[str]
    actual_top_funds: List[str]

    def to_dict(self) -> dict:
        return {
            "window_id": self.window.window_id,
            "train_period": f"{self.window.train_start} to {self.window.train_end}",
            "test_period": f"{self.window.test_start} to {self.window.test_end}",
            "hit_rate": self.hit_rate,
            "hit_count": self.hit_count,
            "total_predictions": self.total_predictions,
            "sharpe_ratio": self.sharpe_ratio,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "weights": self.weights,
        }


class WalkForwardValidator:
    """
    Implements walk-forward validation for fund selection models.

    Example usage:
        validator = WalkForwardValidator(
            database_path="data/fundseeker_nav.db",
            feature_table="features_M_star"
        )

        windows = validator.create_windows(
            start_date="2020-01-01",
            end_date="2025-12-31",
            train_months=24,
            test_months=6,
            step_months=6
        )

        results = validator.run_validation(windows, top_k=30)
        validator.save_results(results, "output/walk_forward_results.json")
    """

    def __init__(self, database_path: str, feature_table: str):
        self.database_path = Path(database_path)
        self.feature_table = feature_table
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.database_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_windows(
        self,
        start_date: str,
        end_date: str,
        train_months: int = 24,
        test_months: int = 6,
        step_months: int = 6,
    ) -> List[ValidationWindow]:
        """
        Create rolling train/test windows for walk-forward validation.

        Args:
            start_date: Start date for the entire period (YYYY-MM-DD)
            end_date: End date for the entire period (YYYY-MM-DD)
            train_months: Number of months for training window
            test_months: Number of months for testing window
            step_months: Number of months to step forward between windows

        Returns:
            List of ValidationWindow objects
        """
        windows = []
        window_id = 1

        # Convert to datetime
        current_train_start = pd.to_datetime(start_date)
        final_date = pd.to_datetime(end_date)

        while True:
            # Calculate window boundaries
            train_end = current_train_start + pd.DateOffset(months=train_months)
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=test_months)

            # Stop if test window exceeds end date
            if test_end > final_date:
                break

            window = ValidationWindow(
                train_start=current_train_start.strftime("%Y-%m-%d"),
                train_end=train_end.strftime("%Y-%m-%d"),
                test_start=test_start.strftime("%Y-%m-%d"),
                test_end=test_end.strftime("%Y-%m-%d"),
                window_id=window_id,
            )
            windows.append(window)

            # Move to next window
            current_train_start += pd.DateOffset(months=step_months)
            window_id += 1

        return windows

    def load_features(
        self, start_date: str, end_date: str, future_horizon_months: int = 6
    ) -> pd.DataFrame:
        """
        Load features and future returns from database.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            future_horizon_months: Months ahead for future returns

        Returns:
            DataFrame with features and future returns
        """
        query = f"""
        SELECT * FROM {self.feature_table}
        WHERE snapshot_date >= ? AND snapshot_date <= ?
        ORDER BY snapshot_date, fund_code
        """

        df = pd.read_sql_query(query, self.conn, params=(start_date, end_date))

        # Add future returns by shifting
        df = df.sort_values(["fund_code", "snapshot_date"])
        df[f"future_ret_{future_horizon_months}m"] = df.groupby("fund_code")[
            f"ret_{future_horizon_months}m"
        ].shift(-1)

        return df

    def optimize_weights(
        self,
        train_df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        grid_step: float = 0.05,
        min_weight: float = 0.0,
        max_weight: float = 0.2,
    ) -> Dict[str, float]:
        """
        Find optimal feature weights using grid search on training data.

        Args:
            train_df: Training data with features and target
            feature_cols: List of feature column names
            target_col: Target column name (future returns)
            grid_step: Step size for grid search
            min_weight: Minimum weight value
            max_weight: Maximum weight value

        Returns:
            Dictionary of optimal weights
        """
        # Remove rows with missing target
        train_df = train_df.dropna(subset=[target_col])

        if len(train_df) == 0:
            raise ValueError("No valid training data after removing NaN targets")

        # Generate weight candidates
        weight_candidates = np.arange(min_weight, max_weight + grid_step, grid_step)

        best_sharpe = -np.inf
        best_weights = None

        # Simple grid search (for demonstration - can be optimized)
        # In practice, you might want to use more sophisticated optimization
        from itertools import product

        # Limit combinations to avoid explosion
        n_features = len(feature_cols)
        if n_features > 5:
            # Use random search for high-dimensional spaces
            n_trials = 1000
            for _ in range(n_trials):
                weights = {
                    col: np.random.choice(weight_candidates) for col in feature_cols
                }
                sharpe = self._evaluate_weights(train_df, weights, feature_cols, target_col)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_weights = weights
        else:
            # Exhaustive grid search for low-dimensional spaces
            for weight_combo in product(weight_candidates, repeat=n_features):
                weights = dict(zip(feature_cols, weight_combo))
                sharpe = self._evaluate_weights(train_df, weights, feature_cols, target_col)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_weights = weights

        return best_weights if best_weights else {col: 0.1 for col in feature_cols}

    def _evaluate_weights(
        self,
        df: pd.DataFrame,
        weights: Dict[str, float],
        feature_cols: List[str],
        target_col: str,
    ) -> float:
        """
        Evaluate a set of weights by calculating Sharpe ratio.

        Returns:
            Sharpe ratio (higher is better)
        """
        # Calculate scores
        feature_matrix = df[feature_cols].fillna(0).to_numpy()
        weight_vector = np.array([weights.get(col, 0.0) for col in feature_cols])
        scores = feature_matrix.dot(weight_vector)

        df = df.copy()
        df["score"] = scores

        # Get top predictions per snapshot
        top_k = 30  # Fixed for evaluation
        df_sorted = df.sort_values(["snapshot_date", "score"], ascending=[True, False])
        top_df = df_sorted.groupby("snapshot_date").head(top_k)

        # Calculate portfolio returns
        portfolio_returns = top_df.groupby("snapshot_date")[target_col].mean()

        if len(portfolio_returns) < 2:
            return -np.inf

        # Calculate Sharpe
        mean_ret = portfolio_returns.mean()
        std_ret = portfolio_returns.std()

        if std_ret == 0 or np.isnan(std_ret):
            return -np.inf

        sharpe = mean_ret / std_ret * np.sqrt(12)  # Annualized
        return sharpe

    def evaluate_on_test(
        self,
        test_df: pd.DataFrame,
        weights: Dict[str, float],
        feature_cols: List[str],
        target_col: str,
        top_k: int = 30,
    ) -> Tuple[float, int, List[str], List[str], float, float, float]:
        """
        Evaluate trained weights on test data.

        Returns:
            Tuple of (hit_rate, hit_count, predicted_funds, actual_top_funds,
                     sharpe, annual_return, max_drawdown)
        """
        test_df = test_df.dropna(subset=[target_col])

        if len(test_df) == 0:
            return 0.0, 0, [], [], 0.0, 0.0, 0.0

        # Calculate scores
        feature_matrix = test_df[feature_cols].fillna(0).to_numpy()
        weight_vector = np.array([weights.get(col, 0.0) for col in feature_cols])
        scores = feature_matrix.dot(weight_vector)

        test_df = test_df.copy()
        test_df["score"] = scores

        # Get predictions and actuals per snapshot
        all_predicted = []
        all_actual_top = []
        hit_counts = []

        for snapshot_date, group in test_df.groupby("snapshot_date"):
            # Predicted top-k
            predicted = group.nlargest(top_k, "score")["fund_code"].tolist()
            all_predicted.extend(predicted)

            # Actual top-k (by future returns)
            actual_top = group.nlargest(top_k, target_col)["fund_code"].tolist()
            all_actual_top.extend(actual_top)

            # Calculate hits
            hits = len(set(predicted) & set(actual_top))
            hit_counts.append(hits)

        # Calculate metrics
        hit_rate = np.mean(hit_counts) / top_k if top_k > 0 else 0.0
        hit_count = int(np.mean(hit_counts))

        # Portfolio performance
        test_df_sorted = test_df.sort_values(["snapshot_date", "score"], ascending=[True, False])
        top_df = test_df_sorted.groupby("snapshot_date").head(top_k)
        portfolio_returns = top_df.groupby("snapshot_date")[target_col].mean()

        if len(portfolio_returns) >= 2:
            mean_ret = portfolio_returns.mean()
            std_ret = portfolio_returns.std()
            annual_return = (1 + mean_ret) ** 12 - 1
            sharpe = mean_ret / std_ret * np.sqrt(12) if std_ret > 0 else 0.0

            # Max drawdown
            cumulative = (1 + portfolio_returns).cumprod()
            max_drawdown = (cumulative / cumulative.cummax() - 1).min()
        else:
            annual_return = 0.0
            sharpe = 0.0
            max_drawdown = 0.0

        return (
            hit_rate,
            hit_count,
            all_predicted[:top_k],  # Return first window's predictions
            all_actual_top[:top_k],
            sharpe,
            annual_return,
            max_drawdown,
        )

    def run_validation(
        self,
        windows: List[ValidationWindow],
        feature_cols: List[str],
        future_horizon_months: int = 6,
        top_k: int = 30,
        grid_step: float = 0.1,
        verbose: bool = True,
    ) -> List[ValidationResult]:
        """
        Run walk-forward validation across all windows.

        Args:
            windows: List of validation windows
            feature_cols: Feature columns to use
            future_horizon_months: Prediction horizon
            top_k: Number of top funds to select
            grid_step: Grid search step size
            verbose: Print progress

        Returns:
            List of ValidationResult objects
        """
        results = []
        target_col = f"future_ret_{future_horizon_months}m"

        for window in windows:
            if verbose:
                print(f"\n{'='*60}")
                print(f"Processing {window}")
                print(f"{'='*60}")

            # Load training data
            train_df = self.load_features(
                window.train_start, window.train_end, future_horizon_months
            )

            if verbose:
                print(f"Training samples: {len(train_df)}")

            # Optimize weights on training data
            if verbose:
                print("Optimizing weights...")

            weights = self.optimize_weights(
                train_df, feature_cols, target_col, grid_step=grid_step
            )

            if verbose:
                print(f"Optimal weights: {weights}")

            # Load test data
            test_df = self.load_features(
                window.test_start, window.test_end, future_horizon_months
            )

            if verbose:
                print(f"Test samples: {len(test_df)}")

            # Evaluate on test data
            (
                hit_rate,
                hit_count,
                predicted_funds,
                actual_top_funds,
                sharpe,
                annual_return,
                max_drawdown,
            ) = self.evaluate_on_test(test_df, weights, feature_cols, target_col, top_k)

            result = ValidationResult(
                window=window,
                hit_rate=hit_rate,
                hit_count=hit_count,
                total_predictions=top_k,
                sharpe_ratio=sharpe,
                annual_return=annual_return,
                max_drawdown=max_drawdown,
                weights=weights,
                predicted_funds=predicted_funds,
                actual_top_funds=actual_top_funds,
            )

            results.append(result)

            if verbose:
                print(f"\nResults:")
                print(f"  Hit Rate: {hit_rate:.2%}")
                print(f"  Hit Count: {hit_count}/{top_k}")
                print(f"  Sharpe: {sharpe:.2f}")
                print(f"  Annual Return: {annual_return:.2%}")
                print(f"  Max Drawdown: {max_drawdown:.2%}")

        return results

    def save_results(self, results: List[ValidationResult], output_path: str) -> None:
        """Save validation results to JSON file."""
        output_data = {
            "summary": {
                "total_windows": len(results),
                "avg_hit_rate": np.mean([r.hit_rate for r in results]),
                "avg_sharpe": np.mean([r.sharpe_ratio for r in results]),
                "avg_annual_return": np.mean([r.annual_return for r in results]),
                "avg_max_drawdown": np.mean([r.max_drawdown for r in results]),
            },
            "windows": [r.to_dict() for r in results],
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {output_file}")

    def generate_report(self, results: List[ValidationResult]) -> str:
        """Generate a text report summarizing validation results."""
        report = []
        report.append("\n" + "=" * 80)
        report.append("WALK-FORWARD VALIDATION REPORT")
        report.append("=" * 80)

        # Summary statistics
        hit_rates = [r.hit_rate for r in results]
        sharpes = [r.sharpe_ratio for r in results]
        returns = [r.annual_return for r in results]
        drawdowns = [r.max_drawdown for r in results]

        report.append("\nOVERALL SUMMARY:")
        report.append(f"  Total Windows: {len(results)}")
        report.append(f"  Average Hit Rate: {np.mean(hit_rates):.2%} (±{np.std(hit_rates):.2%})")
        report.append(f"  Average Sharpe: {np.mean(sharpes):.2f} (±{np.std(sharpes):.2f})")
        report.append(f"  Average Annual Return: {np.mean(returns):.2%} (±{np.std(returns):.2%})")
        report.append(f"  Average Max Drawdown: {np.mean(drawdowns):.2%} (±{np.std(drawdowns):.2%})")

        # Per-window details
        report.append("\n" + "-" * 80)
        report.append("WINDOW-BY-WINDOW RESULTS:")
        report.append("-" * 80)

        for result in results:
            report.append(f"\n{result.window}")
            report.append(f"  Hit Rate: {result.hit_rate:.2%} ({result.hit_count}/{result.total_predictions})")
            report.append(f"  Sharpe: {result.sharpe_ratio:.2f}")
            report.append(f"  Annual Return: {result.annual_return:.2%}")
            report.append(f"  Max Drawdown: {result.max_drawdown:.2%}")

        report.append("\n" + "=" * 80)

        return "\n".join(report)


