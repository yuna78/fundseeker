"""Ranking data fetcher."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import requests


class RankingFetcher:
    """Wraps the Eastmoney ranking endpoint."""

    BASE_URL = "http://fund.eastmoney.com/data/rankhandler.aspx"

    def __init__(self, user_agent: str, timeout: int = 30) -> None:
        self.session = requests.Session()
        self.headers = {
            "User-Agent": user_agent,
            "Referer": "http://fund.eastmoney.com/data/fundranking.html",
        }
        self.timeout = timeout

    def fetch(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 10000,
        sort_field: str = "1nzf",
        sort_direction: str = "desc",
    ) -> pd.DataFrame:
        """Fetch ranking data and parse into a DataFrame."""

        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt.replace(year=end_dt.year - 1)
            start_date = start_date or start_dt.strftime("%Y-%m-%d")
            end_date = end_date or end_dt.strftime("%Y-%m-%d")

        params = {
            "op": "ph",
            "dt": "kf",
            "ft": "all",
            "rs": "",
            "gs": "0",
            "sc": sort_field,
            "st": sort_direction,
            "sd": start_date,
            "ed": end_date,
            "pi": str(page),
            "pn": str(page_size),
            "dx": "1",
            "v": datetime.now().strftime("%H%M%S"),
        }

        response = self.session.get(
            self.BASE_URL,
            params=params,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        parsed = self._parse_content(response.text)
        return self._to_dataframe(parsed)

    def _parse_content(self, content: str) -> Dict[str, any]:
        if "无访问权限" in content or "ErrCode:-999" in content:
            raise RuntimeError("无访问权限，可能触发了接口限制。")

        if "var rankData" not in content:
            raise RuntimeError("响应中未找到 rankData。")

        start_idx = content.find("{")
        end_idx = content.rfind("}") + 1
        json_str = content[start_idx:end_idx]
        json_str = re.sub(r"(\w+):", r'"\1":', json_str)
        return json.loads(json_str)

    def _to_dataframe(self, data: Dict[str, any]) -> pd.DataFrame:
        records = []
        for row in data.get("datas", []):
            fields = row.split(",")
            if len(fields) < 16:
                continue
            record = {
                "基金代码": fields[0],
                "基金简称": fields[1],
                "拼音缩写": fields[2],
                "日期": fields[3],
                "单位净值": fields[4],
                "累计净值": fields[5],
                "日增长率(%)": fields[6],
                "近1周(%)": fields[7],
                "近1月(%)": fields[8],
                "近3月(%)": fields[9],
                "近6月(%)": fields[10],
                "近1年(%)": fields[11],
                "近2年(%)": fields[12],
                "近3年(%)": fields[13],
                "今年来(%)": fields[14],
                "成立来(%)": fields[15],
                "手续费": fields[20] if len(fields) > 20 else "",
                "可购状态": fields[21] if len(fields) > 21 else "",
            }
            records.append(record)

        df = pd.DataFrame(records)
        numeric_columns = [
            "单位净值",
            "累计净值",
            "日增长率(%)",
            "近1周(%)",
            "近1月(%)",
            "近3月(%)",
            "近6月(%)",
            "近1年(%)",
            "近2年(%)",
            "近3年(%)",
            "今年来(%)",
            "成立来(%)",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
