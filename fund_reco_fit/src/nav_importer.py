"""Import FundSeeker outputs (NAV, rank, detail) into SQLite."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import typer


NAV_PATTERN = re.compile(r"nav_(?P<code>\d{6})\.(?:xlsx|csv)", re.IGNORECASE)
RANK_PATTERN = re.compile(r"rank_with_rating_(\d{8})_(\d{6})", re.IGNORECASE)

app = typer.Typer(help="Import NAV / rank / detail outputs into SQLite")


def project_paths() -> Tuple[Path, Path, Path]:
    workspace_root = Path(__file__).resolve().parents[1]  # fund_reco_fit/
    fundseeker_dir = workspace_root.parent / "fundseeker"
    default_output = (fundseeker_dir / "output").resolve()
    default_db = (workspace_root / "data" / "fundseeker_nav.db").resolve()
    return default_output, default_db, workspace_root


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nav_prices (
            fund_code TEXT NOT NULL,
            date TEXT NOT NULL,
            unit_nav REAL,
            accumulated_nav REAL,
            daily_return_percent REAL,
            subscription_status TEXT,
            redemption_status TEXT,
            dividend TEXT,
            source_file TEXT,
            PRIMARY KEY (fund_code, date)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fund_meta (
            fund_code TEXT PRIMARY KEY,
            fund_name TEXT,
            fund_type TEXT,
            fund_size TEXT,
            inception_date TEXT,
            manager TEXT,
            manager_return REAL,
            manager_tenure TEXT,
            updated_at TEXT,
            source_file TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rank_snapshots (
            snapshot_ts TEXT NOT NULL,
            fund_code TEXT NOT NULL,
            fund_name TEXT,
            return_3m REAL,
            return_6m REAL,
            return_1y REAL,
            return_ytd REAL,
            return_2y REAL,
            return_3y REAL,
            rating_avg REAL,
            rating_raw TEXT,
            source_file TEXT,
            PRIMARY KEY (snapshot_ts, fund_code)
        )
        """
    )
    conn.commit()


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"不支持的文件格式: {path}")


def _normalize_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        return value.strip()[:10]
    return ""


def _safe_float(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ""
    return str(value).strip()


def _infer_timestamp(name: str, pattern: re.Pattern) -> Optional[str]:
    match = pattern.search(name)
    if not match:
        return None
    date_str, time_str = match.groups()
    try:
        dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        return dt.isoformat(timespec="seconds")
    except ValueError:
        return None


def import_nav_files(conn: sqlite3.Connection, output_dir: Path) -> int:
    nav_dir = output_dir / "nav"
    files = list(nav_dir.glob("nav_*.xlsx")) + list(nav_dir.glob("nav_*.csv"))
    inserted = 0
    for path in files:
        match = NAV_PATTERN.match(path.name)
        if not match:
            continue
        fund_code = match.group("code")
        df = read_table(path)
        if df.empty or "date" not in df.columns:
            continue
        records = [
            (
                fund_code,
                _normalize_date(row.get("date")),
                _safe_float(row.get("unit_nav")),
                _safe_float(row.get("accumulated_nav")),
                _safe_float(row.get("daily_return_percent")),
                _safe_str(row.get("subscription_status")),
                _safe_str(row.get("redemption_status")),
                _safe_str(row.get("dividend")),
                str(path),
            )
            for _, row in df.iterrows()
            if row.get("date")
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO nav_prices (
                fund_code, date, unit_nav, accumulated_nav, daily_return_percent,
                subscription_status, redemption_status, dividend, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        inserted += len(records)
    conn.commit()
    return inserted


def import_fund_meta(conn: sqlite3.Connection, output_dir: Path) -> int:
    detail_files = sorted(output_dir.glob("fund_details_*.xlsx"))
    if not detail_files:
        return 0
    latest = detail_files[-1]
    df = pd.read_excel(latest)
    if "基金代码" not in df.columns:
        return 0
    records = [
        (
            str(row.get("基金代码")).zfill(6),
            row.get("基金简称"),
            row.get("基金类型"),
            row.get("基金规模"),
            row.get("成立日期"),
            row.get("基金经理"),
            _safe_float(row.get("基金经理任职回报")),
            row.get("基金经理任职期间"),
            datetime.now().isoformat(timespec="seconds"),
            str(latest),
        )
        for _, row in df.iterrows()
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO fund_meta (
            fund_code, fund_name, fund_type, fund_size, inception_date,
            manager, manager_return, manager_tenure, updated_at, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    conn.commit()
    return len(records)


def _calc_rating_avg(df: pd.DataFrame) -> pd.Series:
    rating_cols = [c for c in df.columns if c.startswith("评级字段")]
    if not rating_cols:
        return pd.Series(0.5, index=df.index)
    values = []
    for col in rating_cols:
        series = pd.to_numeric(df[col], errors="coerce").where(lambda s: (s > 0) & (s <= 5))
        if series.dropna().empty:
            continue
        values.append(series / 5.0)
    if not values:
        return pd.Series(0.5, index=df.index)
    stacked = pd.concat(values, axis=1)
    return stacked.mean(axis=1).fillna(0.5)


def _extract_rating_json(row: pd.Series) -> str:
    rating_cols = {k: row[k] for k in row.index if k.startswith("评级字段") and pd.notna(row[k])}
    return json.dumps(rating_cols, ensure_ascii=False) if rating_cols else ""


def import_rank_snapshots(conn: sqlite3.Connection, output_dir: Path) -> int:
    rank_files = sorted(output_dir.glob("rank_with_rating_*.xlsx"))
    imported = 0
    for path in rank_files:
        snapshot_ts = _infer_timestamp(path.name, RANK_PATTERN)
        if not snapshot_ts:
            continue
        df = pd.read_excel(path)
        if "基金代码" not in df.columns:
            continue
        df["rating_avg"] = _calc_rating_avg(df)
        records = [
            (
                snapshot_ts,
                str(row.get("基金代码")).zfill(6),
                row.get("基金简称"),
                _safe_float(row.get("近3月(%)")),
                _safe_float(row.get("近6月(%)")),
                _safe_float(row.get("近1年(%)")),
                _safe_float(row.get("今年来(%)")),
                _safe_float(row.get("近2年(%)")),
                _safe_float(row.get("近3年(%)")),
                row.get("rating_avg"),
                _extract_rating_json(row),
                str(path),
            )
            for _, row in df.iterrows()
        ]
        conn.executemany(
            """
            INSERT OR REPLACE INTO rank_snapshots (
                snapshot_ts, fund_code, fund_name, return_3m, return_6m,
                return_1y, return_ytd, return_2y, return_3y, rating_avg, rating_raw, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        imported += len(records)
    conn.commit()
    return imported


@app.command()
def run(
    fundseeker_output: Optional[Path] = typer.Option(None, help="FundSeeker output 目录"),
    database: Optional[Path] = typer.Option(None, help="SQLite 数据库路径"),
    include_nav: bool = typer.Option(True, help="导入净值"),
    include_meta: bool = typer.Option(True, help="导入基金详情"),
    include_rank: bool = typer.Option(True, help="导入排行快照"),
) -> None:
    default_output, default_db, _ = project_paths()
    output_dir = (fundseeker_output or default_output)
    db_path = (database or default_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        if include_nav:
            typer.echo(f"NAV 导入: {import_nav_files(conn, output_dir)} 条记录更新")
        if include_meta:
            typer.echo(f"基金元数据: {import_fund_meta(conn, output_dir)} 条记录更新")
        if include_rank:
            typer.echo(f"排行快照: {import_rank_snapshots(conn, output_dir)} 条记录更新")
    typer.echo(f"✅ 数据库位置: {db_path}")


if __name__ == "__main__":
    app()
