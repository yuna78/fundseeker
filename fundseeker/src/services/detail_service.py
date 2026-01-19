"""Service handling fund detail enrichment."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from src.data.detail_fetcher import DetailFetcher
from src.utils.config import AppConfig
from src.utils.io_helper import build_output_path, ensure_daily_dir
from src.utils.logger import get_logger


@dataclass
class DetailProgress:
    input_file: str
    output_file: str
    progress_file: str
    total: int
    processed_count: int
    last_index: int
    updated_at: str
    completed: bool


class DetailService:
    REQUIRED_COLUMNS = ("基金代码",)

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = get_logger("details", config.paths.logs_dir)
        self.fetcher = DetailFetcher(
            user_agent=config.settings.user_agent,
            timeout=config.settings.request_timeout,
        )

    def run(self, input_path: Path, auto_resume: bool = True) -> Path:
        input_path = input_path.expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"文件不存在：{input_path}")

        df_input = self._load_input(input_path)
        progress_info = None
        if auto_resume:
            progress_info = self._find_existing_progress(input_path)

        if progress_info:
            self.logger.info("发现进度文件，将从上次进度继续：%s", progress_info.progress_file)
            output_path = Path(progress_info.output_file)
            progress_path = Path(progress_info.progress_file)
            processed = progress_info.processed_count
            last_index = progress_info.last_index
            results = self._load_existing_results(output_path)
        else:
            date_dir = ensure_daily_dir(self.config.paths.progress_dir)
            progress_path = date_dir / f"details_{time.strftime('%Y%m%d_%H%M%S')}.json"
            output_path = build_output_path(self.config.paths.output_dir, "fund_details")
            processed = 0
            last_index = -1
            results: List[dict] = []

        total = len(df_input)

        for idx in range(last_index + 1, total):
            row = df_input.iloc[idx]
            fund_code = str(row["基金代码"]).zfill(6)
            fund_name = row.get("基金简称", "")
            self.logger.info("(%d/%d) 抓取基金 %s %s", idx + 1, total, fund_code, fund_name)
            detail = self.fetcher.fetch_detail(fund_code, fund_name)
            results.append(detail)
            processed += 1
            last_index = idx

            if processed % self.config.settings.save_interval == 0:
                self._persist(results, output_path)
                self._save_progress(progress_path, input_path, output_path, total, processed, last_index, False)
                self.logger.info("已保存进度：%d/%d", processed, total)

            time.sleep(self.config.settings.request_delay)

        self._persist(results, output_path)
        self._save_progress(progress_path, input_path, output_path, total, processed, last_index, True)
        self.logger.info("详情抓取完成：%s", output_path)
        return output_path

    def _load_input(self, path: Path) -> pd.DataFrame:
        if path.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
        else:
            raise ValueError("仅支持 Excel 或 CSV 文件输入")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"缺少必填列: {missing}")

        df["基金代码"] = df["基金代码"].astype(str).str.zfill(6)
        return df

    def _load_existing_results(self, output_path: Path) -> List[dict]:
        if not output_path.exists():
            return []
        df = pd.read_excel(output_path)
        return df.to_dict("records")

    def _persist(self, results: List[dict], output_path: Path) -> None:
        df = pd.DataFrame(results)
        df.to_excel(output_path, index=False)

    def _find_existing_progress(self, input_path: Path) -> Optional[DetailProgress]:
        progress_base = self.config.paths.progress_dir
        if not progress_base.exists():
            return None
        candidates = sorted(
            list(progress_base.glob("*.json")) + list(progress_base.glob("*/*.json")),
            reverse=True,
        )
        for candidate in candidates:
            try:
                with candidate.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:
                continue
            if data.get("input_file") == str(input_path) and not data.get("completed", False):
                return DetailProgress(
                    input_file=data["input_file"],
                    output_file=data["output_file"],
                    progress_file=str(candidate),
                    total=data.get("total", 0),
                    processed_count=data.get("processed_count", 0),
                    last_index=data.get("last_index", -1),
                    updated_at=data.get("updated_at", ""),
                    completed=data.get("completed", False),
                )
        return None

    def _save_progress(
        self,
        progress_path: Path,
        input_path: Path,
        output_path: Path,
        total: int,
        processed: int,
        last_index: int,
        completed: bool,
    ) -> None:
        data = {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "progress_file": str(progress_path),
            "total": total,
            "processed_count": processed,
            "last_index": last_index,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "completed": completed,
        }
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        with progress_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
