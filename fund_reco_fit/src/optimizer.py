"""Optimize factor weights based on feature table and future returns."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import typer

app = typer.Typer(help="Search best factor weights using historical features + future returns.")


@dataclass
class WeightResult:
    weights: Dict[str, float]
    annual_return: float
    sharpe: float
    max_drawdown: float
    hit_rate_top_k: float


FEATURE_COLS = [
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

VOL_SOURCE = {
    3: "vol_3m",
    6: "vol_6m",
    12: "vol_6m",
}


def load_features(conn: sqlite3.Connection, table: str, snapshot_start: Optional[str], snapshot_end: Optional[str]) -> pd.DataFrame:
    query = f"SELECT * FROM {table}"
    params: Tuple = ()
    if snapshot_start and snapshot_end:
        query += " WHERE snapshot_date BETWEEN ? AND ?"
        params = (snapshot_start, snapshot_end)
    elif snapshot_start:
        query += " WHERE snapshot_date >= ?"
        params = (snapshot_start,)
    elif snapshot_end:
        query += " WHERE snapshot_date <= ?"
        params = (snapshot_end,)

    df = pd.read_sql_query(query, conn, params=params, parse_dates=["snapshot_date"])
    return df


def attach_future_returns(df: pd.DataFrame, horizon_months: int) -> tuple[pd.DataFrame, str, Optional[str]]:
    df = df.sort_values(["fund_code", "snapshot_date"]).copy()
    target_ret_col = f"ret_{horizon_months}m"
    if target_ret_col not in df.columns:
        raise ValueError(f"特征表中缺少 {target_ret_col}，请确保 feature_builder 已输出该列。")
    future_ret_col = f"future_{target_ret_col}"
    df[future_ret_col] = df.groupby("fund_code")[target_ret_col].shift(-1)

    penalty_source = VOL_SOURCE.get(horizon_months)
    future_vol_col: Optional[str] = None
    if penalty_source and penalty_source in df.columns:
        future_vol_col = f"future_{penalty_source}"
        df[future_vol_col] = df.groupby("fund_code")[penalty_source].shift(-1)

    df = df.dropna(subset=[future_ret_col])
    return df, future_ret_col, future_vol_col


def evaluate_weights(
    base_df: pd.DataFrame,
    feature_matrix: np.ndarray,
    weight_vector: np.ndarray,
    weight_dict: Dict[str, float],
    target_col: str,
    top_k: int = 50,
) -> WeightResult:
    score = feature_matrix.dot(weight_vector)
    df = base_df.assign(score=score)
    df = df.sort_values(["snapshot_date", "score"], ascending=[True, False])

    top = df.groupby("snapshot_date").head(top_k)
    portfolio_returns = top.groupby("snapshot_date")[target_col].mean().fillna(0)

    cumulative = (1 + portfolio_returns).cumprod()
    ann_return = (1 + portfolio_returns.mean()) ** 12 - 1
    vol = portfolio_returns.std() * math.sqrt(12)
    sharpe = ann_return / vol if vol and vol > 0 else 0
    max_dd = (cumulative / cumulative.cummax() - 1).min()

    medians = df.groupby("snapshot_date")[target_col].median()
    hit = (top[target_col] > top["snapshot_date"].map(medians)).groupby(top["snapshot_date"]).mean()
    hit_rate = hit.mean()

    return WeightResult(weight_dict, ann_return, sharpe, max_dd, hit_rate)


def _parse_weight_caps(raw: str) -> Dict[str, float]:
    caps: Dict[str, float] = {}
    if not raw:
        return caps
    for item in raw.split(","):
        part = item.strip()
        if not part:
            continue
        if "=" not in part:
            raise typer.BadParameter(f"max-weight 参数格式必须为 feature=value，当前为: {part}")
        feature, value = part.split("=", 1)
        feature = feature.strip()
        try:
            caps[feature] = float(value.strip())
        except ValueError as exc:
            raise typer.BadParameter(f"max-weight 中 {feature} 的值无效: {value}") from exc
    return caps


@app.command()
def run(
    database: Optional[Path] = typer.Option(None, help="SQLite DB path"),
    feature_table: str = typer.Option("features_monthly", help="Features table name"),
    snapshot_start: Optional[str] = typer.Option(None, help="Training start date YYYY-MM-DD"),
    snapshot_end: Optional[str] = typer.Option(None, help="Training end date YYYY-MM-DD"),
    output_json: Optional[Path] = typer.Option(None, help="Where to store best weights JSON"),
    grid: str = typer.Option("-0.5,0,0.5", help="Comma-separated weight grid, e.g. '-0.5,0,0.5,1'"),
    top_k: int = typer.Option(50, help="Top N funds per snapshot used for evaluation"),
    min_abs_weight: float = typer.Option(
        0.0,
        help="If >0, skip weight combos where any feature's absolute weight is below the threshold.",
    ),
    max_weight: str = typer.Option(
        "",
        help="Optional caps for specific features，格式 feature=value,feature2=value。",
    ),
    future_horizon: int = typer.Option(
        6,
        help="未来收益评估周期（月），支持 3 / 6 / 12。",
    ),
) -> None:
    workspace = Path(__file__).resolve().parents[1]
    db_path = (database or (workspace / "data" / "fundseeker_nav.db")).resolve()
    if output_json is None:
        output_json = workspace / "models" / "model_params.json"
    output_json.parent.mkdir(parents=True, exist_ok=True)

    if future_horizon not in {3, 6, 12}:
        raise typer.BadParameter("future-horizon 仅支持 3、6、12 个月。")

    with sqlite3.connect(db_path) as conn:
        features = load_features(conn, feature_table, snapshot_start, snapshot_end)
    if features.empty:
        typer.echo("没有可用的特征数据。")
        return

    df, target_col, _ = attach_future_returns(features, horizon_months=future_horizon)
    if df.empty:
        typer.echo("没有足够的未来收益数据。")
        return

    best: Optional[WeightResult] = None
    feature_matrix = df[FEATURE_COLS].to_numpy(dtype=float)
    base_df = df.drop(columns=FEATURE_COLS)
    grid_values = [float(val.strip()) for val in grid.split(",") if val.strip()]
    if not grid_values:
        raise typer.BadParameter("grid 不能为空")
    if min_abs_weight < 0:
        raise typer.BadParameter("min-abs-weight 不能为负数")
    caps = _parse_weight_caps(max_weight)
    for feature in caps:
        if feature not in FEATURE_COLS:
            raise typer.BadParameter(f"max-weight 指定了未知特征: {feature}")

    for combo in product(grid_values, repeat=len(FEATURE_COLS)):
        weight_vector = np.array(combo, dtype=float)
        if np.allclose(weight_vector, 0):
            continue
        if min_abs_weight > 0 and np.any(np.abs(weight_vector) < min_abs_weight):
            continue
        if caps:
            skip = False
            for idx, feature in enumerate(FEATURE_COLS):
                cap = caps.get(feature)
                if cap is not None and weight_vector[idx] > cap:
                    skip = True
                    break
            if skip:
                continue
        weight_dict = dict(zip(FEATURE_COLS, combo))
        result = evaluate_weights(base_df, feature_matrix, weight_vector, weight_dict, target_col, top_k=top_k)
        if best is None or result.sharpe > best.sharpe:
            best = result

    if not best:
        typer.echo("未搜索到合适的权重。")
        return

    data = {
        "weights": best.weights,
        "annual_return": best.annual_return,
        "sharpe": best.sharpe,
        "max_drawdown": best.max_drawdown,
        "hit_rate_top_k": best.hit_rate_top_k,
        "snapshot_range": {"start": snapshot_start, "end": snapshot_end},
    }
    output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"✅ 最优结果已保存到 {output_json}")


if __name__ == "__main__":
    app()
