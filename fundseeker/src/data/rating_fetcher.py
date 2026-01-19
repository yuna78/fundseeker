"""Rating data fetcher."""

from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd
import requests


class RatingFetcher:
    URL = "https://fund.eastmoney.com/data/fundrating.html"

    def __init__(self, user_agent: str, timeout: int = 30) -> None:
        self.session = requests.Session()
        self.headers = {
            "User-Agent": user_agent,
            "Referer": "https://fund.eastmoney.com/",
        }
        self.timeout = timeout

    def fetch(self) -> pd.DataFrame:
        response = self.session.get(self.URL, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        content = response.text

        pattern = r'var fundinfos = "(.*?)";'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise RuntimeError("未在评级页面找到基金数据")

        raw_data = match.group(1)
        return self._parse(raw_data)

    def _parse(self, payload: str) -> pd.DataFrame:
        records: List[Dict[str, str]] = []

        for record in payload.split("_"):
            if not record.strip():
                continue
            fields = record.split("|")
            if len(fields) < 10:
                continue
            entry: Dict[str, str] = {
                "基金代码": fields[0],
                "基金简称": fields[1],
                "基金类型": fields[2],
                "基金经理": fields[3],
                "基金经理代码": fields[4],
                "基金公司": fields[5],
                "基金公司代码": fields[6],
            }
            # Append generic rating columns for remaining fields.
            for idx in range(7, len(fields)):
                entry[f"评级字段{idx:02d}"] = fields[idx]
            records.append(entry)

        return pd.DataFrame(records)
