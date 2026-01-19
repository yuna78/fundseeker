"""
2025 Real Data Validator

This script validates model predictions against actual 2025 performance.
It compares predictions made at different points in 2024 with real 2025 outcomes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


class RealDataValidator2025:
    """
    Validates predictions against actual 2025 performance.

    Example:
        validator = RealDataValidator2025("data/fundseeker_nav.db", "features_M_star")

        # Test prediction made on 2024-12-31 for 6-month horizon
        result = validator.validate_prediction(
            prediction_date="2024-12-31",
            evaluation_date="2025-06-30",
            weights=model_weights,
            top_k=30
        )
    """

    def __init__(self, database_path: str, feature_table: str):
        self.database_path = Path(database_path)
        self.feature_table = feature_table
        self.conn = sqlite3.connect(self.database_path)

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def validate_prediction(
        self,
        prediction_date: str,
        evaluation_date: str,
        weights: Dict[str, float],
        feature_cols: List[str],
        top_k: int = 30,
    ) -> Dict:
        """
        Validate a single prediction against real outcomes.

        Args:
            prediction_date: Date when prediction was made (YYYY-MM-DD)
            evaluation_date: Date to evaluate actual performance (YYYY-MM-DD)
            weights: Model weights to use for prediction
            feature_cols: Feature columns
            top_k: Number of top funds to predict

        Returns:
            Dictionary with validation metrics
        """
        # Load features at prediction date
        pred_df = self._load_snapshot(prediction_date)

        if len(pred_df) == 0:
            return {"error": f"No data found for {prediction_date}"}

        # Calculate prediction scores
        feature_matrix = pred_df[feature_cols].fillna(0).to_numpy()
        weight_vector = np.array([weights.get(col, 0.0) for col in feature_cols])
        scores = feature_matrix.dot(weight_vector)

        pred_df = pred_df.copy()
        pred_df["score"] = scores

        # Get top-k predictions
        predicted_funds = pred_df.nlargest(top_k, "score")["fund_code"].tolist()

        # Load actual performance at evaluation date
        eval_df = self._load_snapshot(evaluation_date)

        if len(eval_df) == 0:
            return {"error": f"No data found for {evaluation_date}"}

        # Calculate actual returns between prediction and evaluation
        actual_returns = self._calculate_actual_returns(
            prediction_date, evaluation_date, predicted_funds
        )

        # Get actual top performers
        actual_top_funds = eval_df.nlargest(top_k, "ret_6m")["fund_code"].tolist()

        # Calculate metrics
        hits = set(predicted_funds) & set(actual_top_funds)
        hit_rate = len(hits) / top_k

        # Average return of predicted funds
        pred_avg_return = np.mean([actual_returns.get(f, 0) for f in predicted_funds])

        # Average return of actual top funds
        actual_avg_return = eval_df.nlargest(top_k, "ret_6m")["ret_6m"].mean()

        return {
            "prediction_date": prediction_date,
            "evaluation_date": evaluation_date,
            "top_k": top_k,
            "hit_count": len(hits),
            "hit_rate": hit_rate,
            "predicted_funds": predicted_funds,
            "actual_top_funds": actual_top_funds,
            "hits": list(hits),
            "predicted_avg_return": pred_avg_return,
            "actual_top_avg_return": actual_avg_return,
            "return_gap": pred_avg_return - actual_avg_return,
        }

    def _load_snapshot(self, snapshot_date: str) -> pd.DataFrame:
        """Load features for a specific snapshot date."""
        query = f"""
        SELECT * FROM {self.feature_table}
        WHERE DATE(snapshot_date) = DATE(?)
        """
        return pd.read_sql_query(query, self.conn, params=(snapshot_date,))

    def _calculate_actual_returns(
        self, start_date: str, end_date: str, fund_codes: List[str]
    ) -> Dict[str, float]:
        """Calculate actual returns for given funds between two dates."""
        query = """
        SELECT fund_code, nav_date, nav_value
        FROM nav_prices
        WHERE fund_code IN ({})
        AND nav_date BETWEEN ? AND ?
        ORDER BY fund_code, nav_date
        """.format(",".join("?" * len(fund_codes)))

        params = fund_codes + [start_date, end_date]
        df = pd.read_sql_query(query, self.conn, params=params)

        returns = {}
        for fund_code, group in df.groupby("fund_code"):
            if len(group) >= 2:
                start_nav = group.iloc[0]["nav_value"]
                end_nav = group.iloc[-1]["nav_value"]
                returns[fund_code] = (end_nav - start_nav) / start_nav

        return returns

    def batch_validate_2025(
        self,
        prediction_dates: List[str],
        weights: Dict[str, float],
        feature_cols: List[str],
        horizon_months: int = 6,
        top_k: int = 30,
    ) -> List[Dict]:
        """
        Validate multiple predictions throughout 2024 against 2025 outcomes.

        Args:
            prediction_dates: List of dates when predictions were made
            weights: Model weights
            feature_cols: Feature columns
            horizon_months: Prediction horizon in months
            top_k: Number of top funds

        Returns:
            List of validation results
        """
        results = []

        for pred_date in prediction_dates:
            # Calculate evaluation date
            pred_dt = pd.to_datetime(pred_date)
            eval_dt = pred_dt + pd.DateOffset(months=horizon_months)
            eval_date = eval_dt.strftime("%Y-%m-%d")

            print(f"\nValidating: {pred_date} → {eval_date}")

            result = self.validate_prediction(
                pred_date, eval_date, weights, feature_cols, top_k
            )

            if "error" not in result:
                results.append(result)
                print(f"  Hit Rate: {result['hit_rate']:.2%}")
                print(f"  Predicted Avg Return: {result['predicted_avg_return']:.2%}")
                print(f"  Actual Top Avg Return: {result['actual_top_avg_return']:.2%}")
            else:
                print(f"  Error: {result['error']}")

        return results

    def generate_2025_report(self, results: List[Dict]) -> str:
        """Generate a comprehensive report for 2025 validation."""
        report = []
        report.append("\n" + "=" * 80)
        report.append("2025 REAL DATA VALIDATION REPORT")
        report.append("=" * 80)

        if not results:
            report.append("\nNo validation results available.")
            return "\n".join(report)

        # Summary statistics
        hit_rates = [r["hit_rate"] for r in results]
        pred_returns = [r["predicted_avg_return"] for r in results]
        actual_returns = [r["actual_top_avg_return"] for r in results]
        gaps = [r["return_gap"] for r in results]

        report.append("\nSUMMARY:")
        report.append(f"  Total Predictions: {len(results)}")
        report.append(f"  Average Hit Rate: {np.mean(hit_rates):.2%}")
        report.append(f"  Median Hit Rate: {np.median(hit_rates):.2%}")
        report.append(f"  Best Hit Rate: {np.max(hit_rates):.2%}")
        report.append(f"  Worst Hit Rate: {np.min(hit_rates):.2%}")
        report.append(f"\n  Predicted Portfolio Avg Return: {np.mean(pred_returns):.2%}")
        report.append(f"  Actual Top Funds Avg Return: {np.mean(actual_returns):.2%}")
        report.append(f"  Average Return Gap: {np.mean(gaps):.2%}")

        report.append("\n" + "-" * 80)
        report.append("DETAILED RESULTS:")
        report.append("-" * 80)

        for r in results:
            report.append(f"\nPrediction: {r['prediction_date']} → {r['evaluation_date']}")
            report.append(f"  Hit Rate: {r['hit_rate']:.2%} ({r['hit_count']}/{r['top_k']})")
            report.append(f"  Predicted Avg Return: {r['predicted_avg_return']:.2%}")
            report.append(f"  Actual Top Avg Return: {r['actual_top_avg_return']:.2%}")
            report.append(f"  Return Gap: {r['return_gap']:.2%}")

        report.append("\n" + "=" * 80)
        return "\n".join(report)

    def save_results(self, results: List[Dict], output_path: str) -> None:
        """Save validation results to JSON."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {output_file}")
