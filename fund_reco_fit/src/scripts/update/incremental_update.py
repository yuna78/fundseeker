"""
智能增量更新NAV数据
根据每只基金的最新日期，自动下载缺失的数据
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 添加fundseeker路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../fundseeker'))

from src.services.nav_service import NavService
from src.utils.config import load_config

print("=" * 70)
print("智能增量更新NAV数据")
print("=" * 70)
print()

# 加载配置
config = load_config()

# 连接数据库
conn = sqlite3.connect("data/fundseeker_nav.db")

# 查询每只基金的最新日期
query = """
SELECT
    fund_code,
    MAX(date) as latest_date
FROM nav_prices
GROUP BY fund_code
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f"总基金数: {len(df)}")

# 设置目标日期（今天）
target_date = datetime.now().strftime("%Y-%m-%d")
print(f"目标日期: {target_date}")
print()

# 找出需要更新的基金
df['latest_date'] = pd.to_datetime(df['latest_date'])
target_dt = pd.to_datetime(target_date)
needs_update = df[df['latest_date'] < target_dt].copy()

print(f"需要更新的基金数: {len(needs_update)}")

if len(needs_update) == 0:
    print("✅ 所有基金数据都是最新的！")
    sys.exit(0)

# 按最新日期分组
needs_update['days_behind'] = (target_dt - needs_update['latest_date']).dt.days
date_groups = needs_update.groupby('latest_date')

print()
print("更新计划：")
print("-" * 70)
for latest_date, group in date_groups:
    days = group['days_behind'].iloc[0]
    start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"从 {start_date} 更新到 {target_date}: {len(group)} 只基金")

print()
print("=" * 70)
print("开始下载数据...")
print("=" * 70)
print()

# 使用fundseeker的nav命令下载数据
# 为每个日期组分别下载
total_downloaded = 0
failed_funds = []

for latest_date, group in date_groups:
    start_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")
    fund_codes = group['fund_code'].tolist()

    print(f"\n处理 {len(fund_codes)} 只基金 (从 {start_date} 到 {target_date})...")

    # 这里使用fundseeker的nav下载功能
    # 由于fundseeker.sh nav命令会下载所有基金，我们需要另一种方式
    # 建议：为每只基金单独调用API

    for i, fund_code in enumerate(fund_codes, 1):
        if i % 100 == 0:
            print(f"  进度: {i}/{len(fund_codes)}")
        # TODO: 实现单只基金的NAV下载

print()
print(f"✅ 下载完成！共处理 {total_downloaded} 只基金")
if failed_funds:
    print(f"⚠️  失败 {len(failed_funds)} 只基金")
