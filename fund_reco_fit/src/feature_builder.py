"""Build rolling features from NAV data stored in SQLite."""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import typer

app = typer.Typer(help="Generate rolling NAV-based features (returns, risk metrics).")


WINDOWS = {
    "1m": 21,   # ~1 trading month
    "3m": 63,
    "6m": 126,
    "12m": 252,
    "24m": 504,
    "36m": 756,
}
MIN_HISTORY_DAYS = WINDOWS["36m"]
MORNINGSTAR_PENALTY = 2.0
EPSILON = 1e-8


def project_paths() -> Path:
    workspace_root = Path(__file__).resolve().parents[1]
    return workspace_root


def load_nav_data(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT fund_code, date, unit_nav FROM nav_prices ORDER BY fund_code, date",
        conn,
        parse_dates=["date"],
    )
    df["unit_nav"] = pd.to_numeric(df["unit_nav"], errors="coerce")
    df = df.dropna(subset=["unit_nav"])
    return df


def compute_features(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    features = []
    resample_freq = "ME" if freq.upper() == "M" else freq

    for fund_code, group in df.groupby("fund_code"):
        group = group.sort_values("date").set_index("date")
        if group.empty or len(group) < MIN_HISTORY_DAYS:
            continue
        ret_daily = group["unit_nav"].pct_change().fillna(0.0)
        group = group.assign(ret_daily=ret_daily)

        for label, window in WINDOWS.items():
            group[f"ret_{label}"] = _rolling_compound(group["ret_daily"], window)

        group["vol_3m"] = group["ret_daily"].rolling(WINDOWS["3m"]).std() * math.sqrt(252)
        group["vol_6m"] = group["ret_daily"].rolling(WINDOWS["6m"]).std() * math.sqrt(252)
        group["max_drawdown_6m"] = _rolling_max_drawdown(group["unit_nav"], WINDOWS["6m"])
        group["calmar_6m"] = group["ret_6m"] / group["max_drawdown_6m"].abs().replace(0, np.nan)
        group["mdd_36m"] = _rolling_max_drawdown(group["unit_nav"], WINDOWS["36m"])

        # 36M annualized return (3 years)
        group["ret_36m_ann"] = (1 + group["ret_36m"]).pow(12 / 36) - 1
        group["downside_vol_36m"] = _rolling_downside_volatility(group["ret_daily"], WINDOWS["36m"])
        group["risk_adj_return"] = group["ret_36m_ann"] - MORNINGSTAR_PENALTY * group["downside_vol_36m"]
        group["morningstar_score"] = group["risk_adj_return"] / (group["downside_vol_36m"].abs() + EPSILON)
        group["momentum_ratio_3m_12m"] = group["ret_3m"] / (group["ret_12m"].abs() + EPSILON)
        group["vol_trend_3m_6m"] = group["vol_3m"] / (group["vol_6m"].abs() + EPSILON)
        group["drawdown_diff_6m_36m"] = group["max_drawdown_6m"] - group["mdd_36m"]

        sampled = group.resample(resample_freq).last()
        sampled["fund_code"] = fund_code
        sampled = sampled.reset_index().rename(columns={"date": "snapshot_date"})
        features.append(sampled)

    if not features:
        return pd.DataFrame()
    result = pd.concat(features, ignore_index=True)
    return result


def _rolling_compound(returns: pd.Series, window: int) -> pd.Series:
    return (1 + returns).rolling(window).apply(lambda x: np.prod(x) - 1, raw=True)


def _rolling_max_drawdown(nav: pd.Series, window: int) -> pd.Series:
    def mdd(arr: np.ndarray) -> float:
        if len(arr) == 0:
            return np.nan
        cumulative = np.maximum.accumulate(arr)
        drawdowns = arr / cumulative - 1
        return drawdowns.min()

    return nav.rolling(window).apply(mdd, raw=True)


def _rolling_downside_volatility(returns: pd.Series, window: int) -> pd.Series:
    def downside(arr: np.ndarray) -> float:
        negatives = arr[arr < 0]
        if len(negatives) == 0:
            return 0.0
        return math.sqrt(np.mean(negatives ** 2)) * math.sqrt(252)

    return returns.rolling(window).apply(downside, raw=True)


@app.command()
def run(
    database: Optional[Path] = typer.Option(None, help="SQLite DB path (default data/fundseeker_nav.db)"),
    freq: str = typer.Option("M", help="Sampling frequency：M(月) / W(周) / D(日)"),
    output_parquet: Optional[Path] = typer.Option(None, help="Optional Parquet output path"),
    table_name: str = typer.Option("features", help="SQLite table to store features"),
    overwrite_table: bool = typer.Option(True, help="Whether to replace existing table"),
) -> None:
    workspace = project_paths()
    db_path = (database or (workspace / "data" / "fundseeker_nav.db")).resolve()
    out_parquet = output_parquet or (workspace / "data" / f"features_{freq}.parquet")
    out_parquet.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    with sqlite3.connect(db_path) as conn:
        nav_df = load_nav_data(conn)
        typer.echo(f"加载净值数据：{len(nav_df):,} 条")
        feat_df = compute_features(nav_df, freq=freq)
        if feat_df.empty:
            typer.echo("未生成任何特征，请确认净值数据是否足够。")
            return

        try:
            meta = pd.read_sql_query("SELECT fund_code, fund_type FROM fund_meta", conn)
        except Exception:
            meta = pd.DataFrame(columns=["fund_code", "fund_type"])
        feat_df = feat_df.merge(meta, on="fund_code", how="left")
        feat_df["fund_type"] = feat_df["fund_type"].fillna("UNKNOWN")
        feat_df["morningstar_percentile"] = (
            feat_df.groupby(["snapshot_date", "fund_type"])["morningstar_score"]
            .rank(method="average", pct=True)
        )
        feat_df["morningstar_percentile"] = feat_df["morningstar_percentile"].fillna(0.0)

        if overwrite_table:
            if_exists = "replace"
        else:
            if_exists = "append"
        feat_df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        typer.echo(f"特征已写入 SQLite 表 `{table_name}`，行数：{len(feat_df):,}")

    try:
        feat_df.to_parquet(out_parquet, index=False)
        typer.echo(f"Parquet 输出：{out_parquet}")
    except ImportError:
        fallback = out_parquet.with_suffix(".csv")
        feat_df.to_csv(fallback, index=False)
        typer.echo(f"⚠️ 未安装 pyarrow/fastparquet，已改为 CSV 输出：{fallback}")


if __name__ == "__main__":
    app()
