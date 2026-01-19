"""Service that orchestrates ranking and rating fetches."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.ranking_fetcher import RankingFetcher
from src.data.rating_fetcher import RatingFetcher
from src.utils.config import AppConfig
from src.utils.io_helper import build_output_path
from src.utils.logger import get_logger


class RankService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.logger = get_logger("rank", config.paths.logs_dir)
        self.ranking_fetcher = RankingFetcher(
            user_agent=config.settings.user_agent,
            timeout=config.settings.request_timeout,
        )
        self.rating_fetcher = RatingFetcher(
            user_agent=config.settings.user_agent,
            timeout=config.settings.request_timeout,
        )

    def run(self, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: Optional[int] = None) -> Path:
        """Fetch ranking & ratings, merge, and write to Excel."""
        if not start_date or not end_date:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            start_date = start_date or start_dt.strftime("%Y-%m-%d")
            end_date = end_date or end_dt.strftime("%Y-%m-%d")

        self.logger.info("开始抓取基金排行数据（%s 至 %s）", start_date, end_date)
        ranking_df = self.ranking_fetcher.fetch(start_date=start_date, end_date=end_date)
        self.logger.info("排行数据获取完成，共 %d 条", len(ranking_df))

        try:
            rating_df = self.rating_fetcher.fetch()
            self.logger.info("评级数据获取完成，共 %d 条", len(rating_df))
        except Exception as exc:
            self.logger.warning("获取评级数据失败：%s，仅输出排行数据", exc)
            rating_df = pd.DataFrame()

        if not rating_df.empty:
            merged_df = ranking_df.merge(rating_df, on="基金代码", how="left", suffixes=("", "_评级"))
        else:
            merged_df = ranking_df

        if limit is not None and limit > 0:
            merged_df = merged_df.head(limit)
            self.logger.info("已限制输出前 %d 条记录", limit)

        output_path = build_output_path(self.config.paths.output_dir, "rank_with_rating")
        merged_df.to_excel(output_path, index=False)
        self.logger.info("数据已导出：%s", output_path)
        return output_path
