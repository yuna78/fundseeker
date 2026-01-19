"""Service layer for downloading and saving NAV histories."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.data.nav_fetcher import NavFetcher
from src.utils.config import AppConfig
from src.utils.io_helper import ensure_dir


class NavService:
    def __init__(self, cfg: AppConfig, fetcher: Optional[NavFetcher] = None):
        self.cfg = cfg
        self.fetcher = fetcher or NavFetcher(timeout=cfg.settings.request_timeout)

    def download(
        self,
        fund_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fmt: str = "excel",
    ) -> Path:
        df = self.fetcher.fetch(fund_code, start_date=start_date, end_date=end_date)
        out_path = self._nav_file_path(fund_code, fmt)

        if fmt == "excel":
            df.to_excel(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)

        return out_path

    def download_from_file(
        self,
        file_path: Path,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fmt: str = "excel",
    ) -> tuple[Dict[str, Path], Dict[str, str]]:
        df = self._load_fund_list(file_path)
        successes: Dict[str, Path] = {}
        errors: Dict[str, str] = {}
        for code in df["基金代码"].astype(str).str.zfill(6).unique():
            try:
                successes[code] = self.download(code, start_date=start_date, end_date=end_date, fmt=fmt)
            except Exception as exc:  # pragma: no cover - network errors
                errors[code] = str(exc)
        return successes, errors

    def _nav_file_path(self, fund_code: str, fmt: str) -> Path:
        suffix = ".xlsx" if fmt == "excel" else ".csv"
        output_dir = ensure_dir(self.cfg.paths.output_dir / "nav")
        return output_dir / f"nav_{fund_code}{suffix}"

    @staticmethod
    def _load_fund_list(file_path: Path) -> pd.DataFrame:
        if not file_path.exists():
            raise FileNotFoundError(f"基金列表不存在：{file_path}")
        if file_path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        if "基金代码" not in df.columns:
            raise ValueError("基金列表缺少必填列：基金代码")
        return df
