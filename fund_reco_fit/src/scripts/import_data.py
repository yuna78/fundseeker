"""简化的数据导入脚本 - 不依赖typer"""

import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path
import pandas as pd

# 配置
WORKSPACE_ROOT = Path(__file__).resolve().parent
FUNDSEEKER_DIR = WORKSPACE_ROOT.parent / "fundseeker"
OUTPUT_DIR = FUNDSEEKER_DIR / "output"
DB_PATH = WORKSPACE_ROOT / "data" / "fundseeker_nav.db"

NAV_PATTERN = re.compile(r"nav_(?P<code>\d{6})\.(?:xlsx|csv)", re.IGNORECASE)
RANK_PATTERN = re.compile(r"rank_with_rating_(\d{8})_(\d{6})", re.IGNORECASE)


def ensure_schema(conn):
    """创建数据库表结构"""
    conn.execute("""
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
    """)
    conn.execute("""
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
    """)
    conn.execute("""
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
    """)
    conn.commit()


def _safe_float(value):
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, str):
        return value.strip()[:10]
    return ""


def import_nav_files(conn, output_dir):
    """导入NAV净值数据"""
    nav_dir = output_dir / "nav"
    files = list(nav_dir.glob("nav_*.xlsx")) + list(nav_dir.glob("nav_*.csv"))
    inserted = 0

    for i, path in enumerate(files):
        if i % 100 == 0:
            print(f"   处理进度: {i}/{len(files)}")

        match = NAV_PATTERN.match(path.name)
        if not match:
            continue

        fund_code = match.group("code")

        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                df = pd.read_excel(path)
            else:
                df = pd.read_csv(path)
        except Exception as e:
            print(f"   ⚠️  读取失败: {path.name} - {e}")
            continue

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

        conn.executemany("""
            INSERT OR REPLACE INTO nav_prices (
                fund_code, date, unit_nav, accumulated_nav, daily_return_percent,
                subscription_status, redemption_status, dividend, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        inserted += len(records)

    conn.commit()
    return inserted


def import_fund_meta(conn, output_dir):
    """导入基金元数据"""
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

    conn.executemany("""
        INSERT OR REPLACE INTO fund_meta (
            fund_code, fund_name, fund_type, fund_size, inception_date,
            manager, manager_return, manager_tenure, updated_at, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    conn.commit()
    return len(records)


def import_rank_snapshots(conn, output_dir):
    """导入排行快照"""
    rank_files = sorted(output_dir.glob("rank_with_rating_*.xlsx"))
    imported = 0

    for path in rank_files:
        match = RANK_PATTERN.search(path.name)
        if not match:
            continue

        date_str, time_str = match.groups()
        try:
            dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
            snapshot_ts = dt.isoformat(timespec="seconds")
        except ValueError:
            continue

        df = pd.read_excel(path)
        if "基金代码" not in df.columns:
            continue

        # 计算评级平均值
        rating_cols = [c for c in df.columns if c.startswith("评级字段")]
        if rating_cols:
            values = []
            for col in rating_cols:
                series = pd.to_numeric(df[col], errors="coerce")
                series = series.where((series > 0) & (series <= 5))
                if not series.dropna().empty:
                    values.append(series / 5.0)
            if values:
                df["rating_avg"] = pd.concat(values, axis=1).mean(axis=1).fillna(0.5)
            else:
                df["rating_avg"] = 0.5
        else:
            df["rating_avg"] = 0.5

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
                json.dumps({k: row[k] for k in row.index if k.startswith("评级字段") and pd.notna(row[k])}, ensure_ascii=False),
                str(path),
            )
            for _, row in df.iterrows()
        ]

        conn.executemany("""
            INSERT OR REPLACE INTO rank_snapshots (
                snapshot_ts, fund_code, fund_name, return_3m, return_6m,
                return_1y, return_ytd, return_2y, return_3y, rating_avg, rating_raw, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        imported += len(records)

    conn.commit()
    return imported


if __name__ == "__main__":
    print("=" * 80)
    print("开始导入数据到数据库")
    print("=" * 80)
    print(f"数据源: {OUTPUT_DIR}")
    print(f"数据库: {DB_PATH}")
    print()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        ensure_schema(conn)

        print("1. 导入NAV净值数据...")
        nav_count = import_nav_files(conn, OUTPUT_DIR)
        print(f"   ✅ NAV数据: {nav_count} 条记录更新")

        print("\n2. 导入基金元数据...")
        meta_count = import_fund_meta(conn, OUTPUT_DIR)
        print(f"   ✅ 基金元数据: {meta_count} 条记录更新")

        print("\n3. 导入排行快照...")
        rank_count = import_rank_snapshots(conn, OUTPUT_DIR)
        print(f"   ✅ 排行快照: {rank_count} 条记录更新")

    print()
    print("=" * 80)
    print("✅ 数据导入完成！")
    print(f"数据库位置: {DB_PATH}")
    print("=" * 80)
