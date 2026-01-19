"""Generate advanced recommendations using SQLite features + model weights."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.utils.config import AdvancedModelConfig
from src.utils.io_helper import ensure_dir


class AdvancedRecommendService:
    def __init__(self, cfg: AdvancedModelConfig, output_dir: Path):
        self.cfg = cfg
        self.output_dir = output_dir

    def save(self, top_n: int = 200, snapshot_date: Optional[str] = None, output_format: str = "excel") -> Path:
        df, snapshot_date_used = self._load_latest_features(snapshot_date=snapshot_date)
        weights = self._load_weights()
        df = self._score(df, weights)
        df = df.sort_values("预测得分", ascending=False).head(top_n).reset_index(drop=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"{snapshot_date_used}_{ts}" if snapshot_date_used else ts
        output = ensure_dir(self.output_dir) / f"recommendations_advanced_{suffix}"
        output_format = output_format.lower()
        if output_format == "csv":
            output = output.with_suffix(".csv")
            df.to_csv(output, index=False)
        else:
            output = output.with_suffix(".xlsx")
            df.to_excel(output, index=False)
        return output

    def _normalize_snapshot_input(self, snapshot_date: str) -> str:
        try:
            dt = datetime.fromisoformat(snapshot_date)
        except ValueError:
            dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d 00:00:00")

    def _load_latest_features(self, snapshot_date: Optional[str] = None) -> tuple[pd.DataFrame, str]:
        db_path = Path(self.cfg.db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"未找到 SQLite 数据库：{db_path}")
        with sqlite3.connect(db_path) as conn:
            if snapshot_date:
                normalized = self._normalize_snapshot_input(snapshot_date)
                query = f"""
                    SELECT *
                    FROM {self.cfg.feature_table}
                    WHERE snapshot_date = ?
                """
                features = pd.read_sql_query(query, conn, params=(normalized,), parse_dates=["snapshot_date"])
            else:
                query = f"""
                    SELECT *
                    FROM {self.cfg.feature_table}
                    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM {self.cfg.feature_table})
                """
                features = pd.read_sql_query(query, conn, parse_dates=["snapshot_date"])
            meta = pd.read_sql_query(
                "SELECT fund_code, fund_name, fund_type, fund_size, manager FROM fund_meta",
                conn,
            )
        if features.empty:
            raise ValueError("未在特征表中找到任何记录，请先运行特征构建。")
        actual_snapshot = features["snapshot_date"].max().date().isoformat()
        merged = features.merge(meta, how="left", on="fund_code", suffixes=("_feat", "_meta"))
        fund_type_meta = merged.get("fund_type_meta")
        fund_type_feat = merged.get("fund_type_feat")
        if fund_type_meta is not None and fund_type_feat is not None:
            merged["fund_type"] = fund_type_meta.fillna(fund_type_feat)
        elif fund_type_meta is not None:
            merged["fund_type"] = fund_type_meta
        elif fund_type_feat is not None:
            merged["fund_type"] = fund_type_feat
        merged = merged.drop(columns=[col for col in merged.columns if col.startswith("fund_type_")])
        return merged, actual_snapshot

    def _load_weights(self) -> Dict[str, float]:
        weights_path = Path(self.cfg.weights_path)
        if not weights_path.exists():
            raise FileNotFoundError(f"未找到权重文件：{weights_path}")
        data = json.loads(weights_path.read_text(encoding="utf-8"))
        weights = data.get("weights") or data
        return {k: float(v) for k, v in weights.items()}

    def _score(self, df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
        feature_cols = [col for col in weights if col in df.columns]
        if not feature_cols:
            raise ValueError("权重中的列在特征表中不存在，请检查模型与特征表是否匹配。")
        weight_vec = np.array([weights[col] for col in feature_cols], dtype=float)
        feature_mat = df[feature_cols].to_numpy(dtype=float)
        df = df.copy()
        df["score"] = feature_mat.dot(weight_vec)
        df["snapshot_date"] = df["snapshot_date"].dt.date
        columns = [
            "fund_code",
            "fund_name",
            "fund_type",
            "fund_size",
            "snapshot_date",
            "score",
        ] + feature_cols
        return df[columns].rename(
            columns={
                "fund_code": "基金代码",
                "fund_name": "基金名称",
                "fund_type": "基金类型",
                "fund_size": "基金规模",
                "snapshot_date": "快照日期",
                "score": "预测得分",
            }
        )
