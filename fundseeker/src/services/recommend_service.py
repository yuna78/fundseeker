"""Generate fund recommendations based on ranking + detail data."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.config import RecommendationWeights
from src.utils.io_helper import ensure_dir


def _latest_file(base_dir: Path, pattern: str) -> Path:
    files = sorted(base_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"未找到 {pattern} 匹配的文件，请先运行抓取流程。")
    return files[-1]


def _parse_scale(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return float("nan")
    text = value.strip()
    if not text:
        return float("nan")
    multiplier = 1.0
    if text.endswith("亿元"):
        text = text[:-2]
    elif text.endswith("亿"):
        text = text[:-1]
    elif text.endswith("万亿元"):
        text = text[:-3]
        multiplier = 10000.0
    text = text.replace(",", "")
    try:
        return float(text) * multiplier
    except ValueError:
        return float("nan")


def _parse_percent(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return float("nan")
    text = value.strip().replace("%", "")
    if not text:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def _normalize(series: pd.Series, temperature: float = 3.0) -> pd.Series:
    """Normalize via percent-rank + logistic smoothing to reduce extremes."""

    result = pd.Series(0.5, index=series.index, dtype=float)
    valid = series.dropna()
    if valid.empty:
        return result

    if len(valid) == 1:
        result.loc[valid.index] = 0.5
        return result

    ranks = valid.rank(method="average", ascending=True)
    percent = (ranks - 1) / (len(valid) - 1)
    scaled = 1 / (1 + np.exp(-temperature * (percent - 0.5)))
    result.loc[scaled.index] = scaled
    return result


def _scale_score(value: float) -> float:
    if math.isnan(value):
        return 0.5
    if value <= 1:
        return 0.1
    if value < 10:
        return 0.1 + 0.9 * (value - 1) / 9
    if value <= 80:
        return 1.0
    if value <= 200:
        return max(0.2, 1 - (value - 80) / 160)
    return 0.1


def _age_score(age_years: float) -> float:
    if math.isnan(age_years):
        return 0.5
    if age_years < 1:
        return 0.3
    if age_years < 3:
        return 0.7
    if age_years <= 10:
        return 1.0
    return 0.8


class RecommendService:
    def __init__(self, output_dir: Path, weights: "RecommendationWeights"):
        self.output_dir = output_dir
        self.weights = weights

    def _load_data(self) -> pd.DataFrame:
        ensure_dir(self.output_dir)
        rank_path = _latest_file(self.output_dir, "rank_with_rating_*.xlsx")
        detail_path = _latest_file(self.output_dir, "fund_details_*.xlsx")

        rank_df = pd.read_excel(rank_path)
        detail_df = pd.read_excel(detail_path)

        detail_df["基金规模(亿元)"] = detail_df["基金规模"].apply(_parse_scale)
        detail_df["基金经理任职回报(%)"] = detail_df["基金经理任职回报"].apply(_parse_percent)
        detail_df["任职年限"] = detail_df["基金经理任职期间"].apply(self._parse_tenure_years)
        detail_df["基金成立年限"] = detail_df["成立日期"].apply(self._parse_fund_age)

        keep_cols = [
            "基金代码",
            "基金规模(亿元)",
            "基金经理任职回报(%)",
            "任职年限",
            "基金成立年限",
        ]
        if "基金经理" in detail_df.columns:
            keep_cols.append("基金经理")
        if "基金类型" in detail_df.columns:
            keep_cols.append("基金类型")
        merged = rank_df.merge(detail_df[keep_cols], on="基金代码", how="inner")
        return merged

    @staticmethod
    def _parse_tenure_years(value) -> float:
        if not isinstance(value, str):
            return float("nan")
        digits = "".join(ch if ch.isdigit() else " " for ch in value)
        parts = [p for p in digits.split() if p]
        if not parts:
            return float("nan")
        years = int(parts[0])
        days = int(parts[1]) if len(parts) > 1 else 0
        return years + days / 365.0

    @staticmethod
    def _parse_fund_age(value) -> float:
        if not isinstance(value, str):
            return float("nan")
        try:
            founded = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return float("nan")
        days = max((datetime.now() - founded).days, 1)
        return days / 365.0

    def compute(self, top_n: int = 200) -> pd.DataFrame:
        df = self._load_data()
        df = self._build_scores(df)

        columns = [
            "基金代码",
            "基金简称",
            "基金规模(亿元)",
            "基金经理任职回报(%)",
            "近3月(%)",
            "近6月(%)",
            "近1年(%)",
            "今年来(%)",
            "近2年(%)",
            "近3年(%)",
            "成立来(%)",
            "近期得分",
            "中期得分",
            "长期得分",
            "风险惩罚",
            "经理得分",
            "规模得分",
            "评级得分",
            "年龄得分",
            "推荐值",
        ]
        if "基金类型" in df.columns:
            columns.insert(2, "基金类型")
        if "基金经理" in df.columns:
            columns.insert(3, "基金经理")

        return (
            df[columns]
            .sort_values("推荐值", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

    def _build_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        df["近期动量"] = 0.5 * df["近6月(%)"] + 0.3 * df["近3月(%)"] + 0.2 * df["近1年(%)"]
        df["近期波动proxy"] = (
            df["近3月(%)"].sub(df["近6月(%)"]).abs() + df["近6月(%)"].abs()
        )
        df["近期收益风险比"] = df["近期动量"] / (df["近期波动proxy"].replace(0, 1))
        df["近期得分"] = _normalize(df["近期收益风险比"])

        df["中期趋势"] = 0.6 * df["今年来(%)"] + 0.4 * df["近2年(%)"]
        df["中期得分"] = _normalize(df["中期趋势"])

        df["历史增速"] = (df["近3年(%)"] - df["今年来(%)"]).fillna(0) / 3
        df["长期组合"] = 0.7 * df["近3年(%)"] + 0.3 * (df["历史增速"] + df["今年来(%)"])
        df["长期得分"] = _normalize(df["长期组合"])

        df["风险惩罚"] = _normalize(
            df["近1年(%)"].sub(df["近2年(%)"] / 2).abs()
            + df["近3月(%)"].sub(df["近6月(%)"]).abs()
        )

        df["经理得分"] = _normalize(
            df["基金经理任职回报(%)"] * df["任职年限"].fillna(0).clip(lower=0.5) ** 0.5
        )
        df["规模得分"] = df["基金规模(亿元)"].apply(_scale_score)
        df["年龄得分"] = df["基金成立年限"].apply(_age_score)
        df["评级得分"] = self._build_rating_score(df)

        w = self.weights
        df["推荐值"] = (
            w.recent * df["近期得分"]
            + w.mid * df["中期得分"]
            + w.long * df["长期得分"]
            - w.risk_penalty * df["风险惩罚"]
            + w.manager * df["经理得分"]
            + w.scale * df["规模得分"]
            + w.rating * df["评级得分"]
            + w.age * df["年龄得分"]
        )
        return df

    def _build_rating_score(self, df: pd.DataFrame) -> pd.Series:
        rating_cols = [c for c in df.columns if c.startswith("评级字段")]
        scaled = []
        for col in rating_cols:
            series = pd.to_numeric(df[col], errors="coerce")
            series = series.where(series > 0)
            series = series.where(series <= 5)
            if series.dropna().empty:
                continue
            scaled.append(series / 5.0)
        if not scaled:
            return pd.Series(0.5, index=df.index)
        stacked = pd.concat(scaled, axis=1)
        return stacked.mean(axis=1).fillna(0.5)

    def save(self, top_n: int = 200) -> Path:
        data = self.compute(top_n)
        path = self.output_dir / f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        data.to_excel(path, index=False)
        return path
