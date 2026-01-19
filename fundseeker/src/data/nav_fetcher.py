"""Fetch historical NAV data for a specific fund from Eastmoney."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import requests

DEFAULT_API = "https://api.fund.eastmoney.com/f10/lsjz"


@dataclass
class NavRecord:
    date: str
    unit_nav: float
    accumulated_nav: float
    daily_return_percent: float
    subscription_status: str
    redemption_status: str
    dividend: str


class NavFetcher:
    """Retrieve fund NAV history via Eastmoney public API."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: int = 30):
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch(
        self,
        fund_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_size: int = 200,
    ) -> pd.DataFrame:
        fund_code = fund_code.strip()
        if not fund_code:
            raise ValueError("基金代码不能为空")

        headers = {
            "Referer": "https://fundf10.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        params = {
            "fundCode": fund_code,
            "pageIndex": 1,
            "pageSize": page_size,
            "startDate": start_date or "",
            "endDate": end_date or "",
        }

        records: List[NavRecord] = []
        total_count: Optional[int] = None

        while True:
            params["_"] = int(time.time() * 1000)
            resp = self.session.get(DEFAULT_API, params=params, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json().get("Data") or {}

            if total_count is None and "TotalCount" in data:
                total_count = int(data.get("TotalCount") or 0)

            page_items = data.get("LSJZList") or []
            if not page_items:
                break

            for item in page_items:
                records.append(
                    NavRecord(
                        date=item.get("FSRQ") or item.get("JZRQ"),
                        unit_nav=_safe_float(item.get("DWJZ")),
                        accumulated_nav=_safe_float(item.get("LJJZ")),
                        daily_return_percent=_safe_float(item.get("JZZZL")),
                        subscription_status=(item.get("SGZT") or "").strip(),
                        redemption_status=(item.get("SHZT") or "").strip(),
                        dividend=(item.get("FHSP") or "").strip(),
                    )
                )

            if total_count is not None and len(records) >= total_count:
                break

            params["pageIndex"] += 1

        if not records:
            raise ValueError(f"未获取到基金 {fund_code} 的净值数据，可能需要更换日期区间或稍后重试。")

        df = pd.DataFrame([r.__dict__ for r in records])
        df["fund_code"] = fund_code
        return df.sort_values("date", ascending=False).reset_index(drop=True)


def _safe_float(value) -> float:
    try:
        if value in ("", None):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
