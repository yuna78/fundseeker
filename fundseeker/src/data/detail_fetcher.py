"""Fund detail fetcher."""

from __future__ import annotations

import re
from typing import Dict

import requests


class DetailFetcher:
    """Fetch fund base info and manager data from Eastmoney."""

    def __init__(self, user_agent: str, timeout: int = 10) -> None:
        self.session = requests.Session()
        self.headers = {"User-Agent": user_agent}
        self.timeout = timeout

    def fetch_manager_info(self, fund_code: str) -> Dict[str, str]:
        url = f"http://fundf10.eastmoney.com/jjjl_{fund_code}.html"
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        response.encoding = "utf-8"
        content = response.text

        info = {
            "基金经理上任日期": "",
            "基金经理任职期间": "",
            "基金经理任职回报": "",
        }

        section_pattern = r"基金经理变动一览.*?<table[^>]*>(.*?)</table>"
        section_match = re.search(section_pattern, content, re.DOTALL)
        if section_match:
            table_html = section_match.group(0)
            row_pattern = r"<tr[^>]*>(.*?)</tr>"
            rows = re.findall(row_pattern, table_html, re.DOTALL)
            if len(rows) >= 2:
                data_row = rows[1]
                cell_pattern = r"<t[dh][^>]*>(.*?)</t[dh]>"
                cells = re.findall(cell_pattern, data_row, re.DOTALL)
                clean = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
                if len(clean) >= 5 and clean[1] in {"至今", "---"}:
                    info["基金经理上任日期"] = clean[0]
                    info["基金经理任职期间"] = clean[3]
                    info["基金经理任职回报"] = clean[4]

        if not info["基金经理上任日期"]:
            appoint_match = re.search(r"<strong>上任日期：</strong>\s*([0-9-]+)", content)
            if appoint_match:
                info["基金经理上任日期"] = appoint_match.group(1)

        return info

    def fetch_detail(self, fund_code: str, fund_name: str = "") -> Dict[str, str]:
        url = f"http://fund.eastmoney.com/{fund_code}.html"
        response = self.session.get(url, headers=self.headers, timeout=self.timeout)
        response.encoding = "utf-8"
        content = response.text

        detail = {
            "基金代码": fund_code,
            "基金名称": fund_name,
            "基金规模": "",
            "成立日期": "",
            "基金经理": "",
            "基金经理详情页": f"http://fundf10.eastmoney.com/jjjl_{fund_code}.html",
            "基金经理上任日期": "",
            "基金经理任职期间": "",
            "基金经理任职回报": "",
        }

        if not fund_name:
            name_match = re.search(
                r'<div[^>]*class="fundDetail-tit"[^>]*>.*?<div[^>]*>([^<(]+)',
                content,
                re.DOTALL,
            )
            if name_match:
                detail["基金名称"] = name_match.group(1).strip()

        scale_match = re.search(r">规模</a>[：:]([\d.]+[亿万]?元)[（(]([0-9-]+)[）)]", content)
        if scale_match:
            detail["基金规模"] = scale_match.group(1)

        date_match = re.search(r'letterSpace01">成\s*立\s*日</span>[：:]\s*([0-9-]+)', content)
        if date_match:
            detail["成立日期"] = date_match.group(1)

        manager_match = re.search(r"基金经理[：:].*?<a[^>]*>([^<]+)</a>", content)
        if manager_match:
            detail["基金经理"] = manager_match.group(1)

        detail.update(self.fetch_manager_info(fund_code))
        return detail
