"""Fit cross-sectional weights that best explain next-period returns."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np
import pandas as pd
import typer

DEFAULT_FEATURES: Sequence[str] = (
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
)

app = typer.Typer(help="Cross-sectional ridge regression to fit weights from one snapshot to the next.")


@dataclass
class FitResult:
    weights: dict
    hit_count: int
    hit_rate: float
    actual_top_avg: float
    predicted_top_avg: float


def _load_snapshot(conn: sqlite3.Connection, table: str, snapshot: str, columns: Sequence[str] | None = None) -> pd.DataFrame:
    select_cols = ", ".join(columns) if columns else "*"
    query = f"SELECT {select_cols} FROM {table} WHERE snapshot_date = ?"
    df = pd.read_sql_query(query, conn, params=(snapshot,), parse_dates=["snapshot_date"])
    df["fund_code"] = df["fund_code"].astype(str).str.zfill(6)
    return df


def _ridge_fit(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    XtX = X.T @ X + lam * np.eye(X.shape[1], dtype=float)
    XtY = X.T @ y
    return np.linalg.solve(XtX, XtY)


def fit_weights(
    database: Path,
    feature_table: str,
    snapshot_train: str,
    snapshot_target: str,
    feature_cols: Sequence[str],
    target_horizon: int,
    ridge_lambda: float,
    top_k: int,
) -> FitResult:
    with sqlite3.connect(database) as conn:
        train_df = _load_snapshot(conn, feature_table, snapshot_train)
        target_cols = ["fund_code", f"ret_{target_horizon}m"]
        target_df = _load_snapshot(conn, feature_table, snapshot_target, columns=target_cols)

    merged = train_df.merge(target_df, on="fund_code", how="inner", suffixes=("", "_future"))
    target_col = f"ret_{target_horizon}m"
    target_name = f"{target_col}_future"
    merged = merged.dropna(subset=[target_name])

    active_features = [col for col in feature_cols if col in merged.columns]
    if not active_features:
        raise ValueError("没有可用的特征列，请检查 feature_table 是否包含所需列。")

    X = merged[active_features].fillna(0.0).to_numpy(dtype=float)
    y = merged[target_name].to_numpy(dtype=float)
    weights = _ridge_fit(X, y, ridge_lambda)

    merged = merged.assign(pred_score=X @ weights)
    actual_top = set(merged.sort_values(target_name, ascending=False).head(top_k)["fund_code"])
    predicted = merged.sort_values("pred_score", ascending=False).head(top_k)
    pred_top = set(predicted["fund_code"])
    hits = actual_top & pred_top

    return FitResult(
        weights=dict(zip(active_features, weights)),
        hit_count=len(hits),
        hit_rate=len(hits) / top_k if top_k else 0.0,
        actual_top_avg=merged.loc[merged["fund_code"].isin(actual_top), target_name].mean(),
        predicted_top_avg=merged.loc[merged["fund_code"].isin(pred_top), target_name].mean(),
    )


@app.command()
def run(
    database: Path = typer.Option(Path("data/fundseeker_nav.db"), "--database", help="SQLite 数据库路径"),
    feature_table: str = typer.Option("features_M_star", help="特征表名"),
    snapshot_train: str = typer.Option(..., help="训练快照日期，格式 YYYY-MM-DD HH:MM:SS"),
    snapshot_target: str = typer.Option(..., help="目标快照日期，格式 YYYY-MM-DD HH:MM:SS"),
    target_horizon: int = typer.Option(12, help="预测目标对应的收益窗口（月）"),
    ridge_lambda: float = typer.Option(0.1, help="岭回归正则系数 λ"),
    top_k: int = typer.Option(30, help="用于评估命中率的 Top K 数量"),
    features: List[str] = typer.Option(None, help="自定义特征列（默认使用内置列表）"),
    output_json: Path = typer.Option(
        Path("models/model_params_crosssec.json"), "--output-json", help="保存权重的 JSON 路径"
    ),
):
    """Fit cross-sectional weights from snapshot_train to snapshot_target."""
    db_path = database.resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在：{db_path}")

    feat_cols = features or DEFAULT_FEATURES
    train_snapshot = snapshot_train.strip()
    target_snapshot = snapshot_target.strip()

    result = fit_weights(
        db_path,
        feature_table,
        train_snapshot,
        target_snapshot,
        feat_cols,
        target_horizon,
        ridge_lambda,
        top_k,
    )

    payload = {
        "weights": result.weights,
        "method": "cross_sectional_ridge",
        "ridge_lambda": ridge_lambda,
        "snapshot_train": train_snapshot,
        "snapshot_target": target_snapshot,
        "target_horizon_months": target_horizon,
        "hit_count_top_k": result.hit_count,
        "hit_rate_top_k": result.hit_rate,
        "actual_top_avg_return": result.actual_top_avg,
        "predicted_top_avg_return": result.predicted_top_avg,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    typer.echo(f"✔ 权重已写入 {output_json}")
    typer.echo(f"Top {top_k} 命中 {result.hit_count} 只基金，命中率 {result.hit_rate:.2%}")


if __name__ == "__main__":
    app()
