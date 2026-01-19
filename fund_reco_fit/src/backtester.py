"""Walk-forward evaluation for advanced NAV-based recommendations."""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import typer

from .optimizer import FEATURE_COLS, TARGET_COL

app = typer.Typer(help="Evaluate model weights using historical features + future returns.")


def load_features(
    conn: sqlite3.Connection,
    table: str,
    snapshot_start: Optional[str],
    snapshot_end: Optional[str],
) -> pd.DataFrame:
    query = f"SELECT * FROM {table}"
    params = []
    if snapshot_start and snapshot_end:
        query += " WHERE snapshot_date BETWEEN ? AND ?"
        params = [snapshot_start, snapshot_end]
    elif snapshot_start:
        query += " WHERE snapshot_date >= ?"
        params = [snapshot_start]
    elif snapshot_end:
        query += " WHERE snapshot_date <= ?"
        params = [snapshot_end]
    return pd.read_sql_query(query, conn, params=params, parse_dates=["snapshot_date"])


def attach_future_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["fund_code", "snapshot_date"]).copy()
    df[TARGET_COL] = df.groupby("fund_code")["ret_3m"].shift(-1)
    df["future_vol_3m"] = df.groupby("fund_code")["vol_3m"].shift(-1)
    df = df.dropna(subset=[TARGET_COL])
    return df


def evaluate(df: pd.DataFrame, weights: Dict[str, float], top_k: int) -> Dict[str, float]:
    feature_matrix = df[FEATURE_COLS].to_numpy(dtype=float)
    weight_vector = np.array([weights.get(col, 0.0) for col in FEATURE_COLS], dtype=float)
    scores = feature_matrix.dot(weight_vector)
    df = df.assign(score=scores)
    df = df.sort_values(["snapshot_date", "score"], ascending=[True, False])
    top = df.groupby("snapshot_date").head(top_k)
    portfolio_returns = top.groupby("snapshot_date")[TARGET_COL].mean().fillna(0)

    cumulative = (1 + portfolio_returns).cumprod()
    ann_return = (1 + portfolio_returns.mean()) ** 12 - 1
    vol = portfolio_returns.std() * math.sqrt(12)
    sharpe = ann_return / vol if vol and vol > 0 else 0.0
    max_dd = (cumulative / cumulative.cummax() - 1).min()

    medians = df.groupby("snapshot_date")[TARGET_COL].median()
    hit_ratio = (top[TARGET_COL] > top["snapshot_date"].map(medians)).groupby(top["snapshot_date"]).mean().mean()

    return {
        "annual_return": ann_return,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "hit_rate": hit_ratio,
    }


def load_weights(path: Path) -> Dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("weights", data)


@app.command()
def run(
    database: Optional[Path] = typer.Option(None, help="SQLite DB path"),
    feature_table: str = typer.Option("features_monthly", help="Features table"),
    weights_json: Path = typer.Option(..., exists=True, help="Model params JSON (包含 weights 字段)"),
    snapshot_start: Optional[str] = typer.Option(None, help="开始日期 YYYY-MM-DD"),
    snapshot_end: Optional[str] = typer.Option(None, help="结束日期 YYYY-MM-DD"),
    top_k: int = typer.Option(50, help="每个时间点取前 N 个基金"),
    output_csv: Optional[Path] = typer.Option(None, help="若指定，则输出按期收益 CSV"),
) -> None:
    workspace = Path(__file__).resolve().parents[1]
    db_path = (database or (workspace / "data" / "fundseeker_nav.db")).resolve()
    if output_csv is None:
        output_csv = workspace / "output" / "advanced_backtest.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    weights = load_weights(weights_json)

    with sqlite3.connect(db_path) as conn:
        features = load_features(conn, feature_table, snapshot_start, snapshot_end)
    if features.empty:
        typer.echo("未找到特征数据，请先运行 feature_builder。")
        return
    df = attach_future_returns(features)
    if df.empty:
        typer.echo("无 future returns，可能训练区间过短。")
        return

    metrics = evaluate(df, weights, top_k)
    typer.echo(f"权重来源: {weights_json}")
    typer.echo(f"年化收益: {metrics['annual_return']:.2%}")
    typer.echo(f"Sharpe: {metrics['sharpe']:.2f}")
    typer.echo(f"最大回撤: {metrics['max_drawdown']:.2%}")
    typer.echo(f"Top{top_k} 命中率: {metrics['hit_rate']:.2%}")

    portfolio_returns = (
        df.assign(score=np.dot(df[FEATURE_COLS], np.array([weights.get(col, 0.0) for col in FEATURE_COLS])) )
        .sort_values(["snapshot_date", "score"], ascending=[True, False])
        .groupby("snapshot_date")
        .head(top_k)
        .groupby("snapshot_date")[TARGET_COL]
        .mean()
        .reset_index()
        .rename(columns={TARGET_COL: "future_ret"})
    )
    portfolio_returns.to_csv(output_csv, index=False)
    typer.echo(f"逐期收益已导出: {output_csv}")


if __name__ == "__main__":
    app()
