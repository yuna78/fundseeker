"""
CLI for running walk-forward validation and 2025 real data validation.

Usage:
    # Run walk-forward validation
    python -m src.run_validation walk-forward \
        --database data/fundseeker_nav.db \
        --start-date 2020-01-01 \
        --end-date 2025-12-31 \
        --train-months 24 \
        --test-months 6 \
        --step-months 6

    # Validate against 2025 real data
    python -m src.run_validation validate-2025 \
        --database data/fundseeker_nav.db \
        --weights-json models/model_params_6m.json \
        --prediction-dates 2024-06-30,2024-12-31
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import typer

from src.validator_2025 import RealDataValidator2025
from src.walk_forward_validator import WalkForwardValidator

app = typer.Typer(help="Model validation tools")

# Default feature columns
DEFAULT_FEATURES = [
    "ret_1m",
    "ret_3m",
    "ret_6m",
    "ret_12m",
    "ret_24m",
    "ret_36m",
    "risk_adj_return",
    "downside_vol_36m",
    "mdd_36m",
    "morningstar_score",
    "momentum_ratio_3m_12m",
    "vol_trend_3m_6m",
    "drawdown_diff_6m_36m",
]


@app.command()
def walk_forward(
    database: str = typer.Option("data/fundseeker_nav.db", help="SQLite database path"),
    feature_table: str = typer.Option("features_M_star", help="Feature table name"),
    start_date: str = typer.Option("2020-01-01", help="Start date YYYY-MM-DD"),
    end_date: str = typer.Option("2025-12-31", help="End date YYYY-MM-DD"),
    train_months: int = typer.Option(24, help="Training window size in months"),
    test_months: int = typer.Option(6, help="Test window size in months"),
    step_months: int = typer.Option(6, help="Step size in months"),
    top_k: int = typer.Option(30, help="Number of top funds to select"),
    grid_step: float = typer.Option(0.1, help="Grid search step size"),
    output_json: str = typer.Option("output/walk_forward_results.json", help="Output JSON path"),
) -> None:
    """Run walk-forward validation across multiple time windows."""

    typer.echo("🚀 Starting Walk-Forward Validation...")
    typer.echo(f"Database: {database}")
    typer.echo(f"Period: {start_date} to {end_date}")
    typer.echo(f"Train: {train_months}m, Test: {test_months}m, Step: {step_months}m")

    with WalkForwardValidator(database, feature_table) as validator:
        # Create windows
        windows = validator.create_windows(
            start_date, end_date, train_months, test_months, step_months
        )

        typer.echo(f"\n📊 Created {len(windows)} validation windows:")
        for w in windows:
            typer.echo(f"  {w}")

        # Run validation
        results = validator.run_validation(
            windows, DEFAULT_FEATURES, future_horizon_months=test_months,
            top_k=top_k, grid_step=grid_step
        )

        # Save results
        validator.save_results(results, output_json)

        # Print report
        report = validator.generate_report(results)
        typer.echo(report)


@app.command()
def validate_2025(
    database: str = typer.Option("data/fundseeker_nav.db", help="SQLite database path"),
    feature_table: str = typer.Option("features_M_star", help="Feature table name"),
    weights_json: str = typer.Option("models/model_params_6m.json", help="Model weights JSON"),
    prediction_dates: str = typer.Option(
        "2024-06-30,2024-12-31", help="Comma-separated prediction dates"
    ),
    horizon_months: int = typer.Option(6, help="Prediction horizon in months"),
    top_k: int = typer.Option(30, help="Number of top funds"),
    output_json: str = typer.Option("output/validation_2025_results.json", help="Output path"),
) -> None:
    """Validate model predictions against actual 2025 performance."""

    typer.echo("🎯 Starting 2025 Real Data Validation...")

    # Load weights
    with open(weights_json, "r") as f:
        model_data = json.load(f)
        weights = model_data.get("weights", {})

    typer.echo(f"Loaded weights from: {weights_json}")

    # Parse prediction dates
    pred_dates = [d.strip() for d in prediction_dates.split(",")]

    validator = RealDataValidator2025(database, feature_table)

    # Run validation
    results = validator.batch_validate_2025(
        pred_dates, weights, DEFAULT_FEATURES, horizon_months, top_k
    )

    # Save results
    validator.save_results(results, output_json)

    # Print report
    report = validator.generate_2025_report(results)
    typer.echo(report)


if __name__ == "__main__":
    app()
