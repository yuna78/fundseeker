"""
检查每只基金的最新NAV数据日期，生成需要更新的基金列表
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# 连接数据库
conn = sqlite3.connect("data/fundseeker_nav.db")

print("=" * 70)
print("检查每只基金的最新NAV数据日期")
print("=" * 70)
print()

# 查询每只基金的最新日期
query = """
SELECT
    fund_code,
    MAX(date) as latest_date,
    COUNT(*) as record_count
FROM nav_prices
GROUP BY fund_code
ORDER BY latest_date DESC
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f"总基金数: {len(df)}")
print()

# 统计不同最新日期的基金数量
date_stats = df.groupby('latest_date').size().reset_index(name='fund_count')
date_stats = date_stats.sort_values('latest_date', ascending=False)

print("不同最新日期的基金分布：")
print("-" * 70)
for _, row in date_stats.head(10).iterrows():
    print(f"{row['latest_date']}: {row['fund_count']} 只基金")

print()
print("=" * 70)

# 设置目标日期（今天）
target_date = datetime.now().strftime("%Y-%m-%d")
print(f"目标日期: {target_date}")
print()

# 找出需要更新的基金（最新日期 < 目标日期）
df['latest_date'] = pd.to_datetime(df['latest_date'])
target_dt = pd.to_datetime(target_date)
needs_update = df[df['latest_date'] < target_dt].copy()

print(f"需要更新的基金数: {len(needs_update)}")
print()

# 按最新日期分组，生成更新计划
if len(needs_update) > 0:
    needs_update['days_behind'] = (target_dt - needs_update['latest_date']).dt.days

    print("更新计划：")
    print("-" * 70)

    # 按落后天数分组
    for days in sorted(needs_update['days_behind'].unique()):
        funds = needs_update[needs_update['days_behind'] == days]
        latest = funds['latest_date'].iloc[0].strftime("%Y-%m-%d")
        print(f"落后 {days} 天 (最新: {latest}): {len(funds)} 只基金")

    # 保存需要更新的基金列表
    output_file = "funds_need_update.csv"
    needs_update[['fund_code', 'latest_date', 'days_behind']].to_csv(output_file, index=False)
    print()
    print(f"✅ 需要更新的基金列表已保存到: {output_file}")
else:
    print("✅ 所有基金数据都是最新的！")
