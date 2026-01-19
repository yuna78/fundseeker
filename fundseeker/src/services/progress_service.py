"""Service to inspect progress files."""

from __future__ import annotations

import json
from typing import Optional

from src.utils.config import AppConfig
from src.utils.io_helper import ensure_daily_dir
from src.utils.logger import get_logger


class ProgressService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = get_logger("progress", config.paths.logs_dir)

    def show(self, date: Optional[str] = None) -> None:
        base_dir = ensure_daily_dir(self.config.paths.progress_dir)
        files = sorted(base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            self.logger.info("未找到进度文件。")
            return

        if date:
            files = [f for f in files if date in f.name]
            if not files:
                self.logger.info("未找到包含 %s 的进度文件。", date)
                return

        for file in files:
            with file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            processed = data.get("processed_count", 0)
            total = data.get("total", 0) or 1
            percent = processed / total * 100
            self.logger.info(
                "%s | %d/%d (%.2f%%) | 输入: %s | 输出: %s | 更新时间: %s | 完成: %s",
                file.name,
                processed,
                total,
                percent,
                data.get("input_file"),
                data.get("output_file"),
                data.get("updated_at"),
                data.get("completed"),
            )
