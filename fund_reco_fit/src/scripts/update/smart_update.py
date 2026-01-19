"""
智能增量更新NAV数据 - 简化版
策略：按最新日期分组，为每组生成基金列表，然后调用fundseeker批量下载
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

print("=" * 70)
print("智能增量更新NAV数据")
print("=" * 70)
print()

# 连接数据库
conn = sqlite3.connect("data/fundseeker_nav.db")

# 查询每只基金的最新日期
query = """
SELECT fund_code, MAX(date) as latest_date
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
print()

if len(needs_update) == 0:
    print("✅ 所有基金数据都是最新的！")
    exit(0)

# 按最新日期分组
needs_update['start_date'] = needs_update['latest_date'] + timedelta(days=1)
date_groups = needs_update.groupby('start_date')

print("更新计划：")
print("-" * 70)
batch_files = []

for start_date, group in date_groups:
    start_str = start_date.strftime("%Y-%m-%d")
    print(f"从 {start_str} 更新: {len(group)} 只基金")

    # 生成基金列表文件
    batch_file = f"batch_update_{start_str.replace('-', '')}.csv"
    group[['fund_code']].to_csv(batch_file, index=False, header=False)
    batch_files.append((batch_file, start_str))
    print(f"  → 已生成: {batch_file}")

print()
print("=" * 70)
print("下一步操作指南")
print("=" * 70)
print()
print("已为您生成以下批次文件，请按顺序执行：")
print()

for i, (batch_file, start_date) in enumerate(batch_files, 1):
    print(f"批次 {i}:")
    print(f"  cd ../fundseeker")
    print(f"  ./fundseeker.sh nav --input ../fund_reco_fit/{batch_file} --start-date {start_date}")
    print()

print("所有批次完成后，运行以下命令导入数据：")
print("  cd ../fund_reco_fit")
print("  .venv/bin/python import_data_simple.py")
print()
print("=" * 70)
