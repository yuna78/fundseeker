"""
用最佳模型预测2026年上半年表现最好的基金

使用方法：
    python predict_2026.py

输出：
    - 预测的前30只基金列表
    - 保存到 output/prediction_2026_H1.xlsx
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime

# 配置
DATABASE = "data/fundseeker_nav.db"
FEATURE_TABLE = "features_M_star"
MODEL_FILE = "models/model_params_top200.json"  # 使用top200模型
PREDICTION_DATE = "2025-12-31"  # 用2025年12月31日的数据预测
TOP_K = 200  # 前200名（命中率87%）

print("=" * 80)
print("🔮 预测2026年上半年表现最好的基金")
print("=" * 80)
print(f"使用模型: {MODEL_FILE}")
print(f"预测日期: {PREDICTION_DATE}")
print(f"选择数量: 前{TOP_K}只基金")
print()

# 加载模型
with open(MODEL_FILE, "r") as f:
    model_data = json.load(f)
    weights = model_data["weights"]
    hit_rate = model_data.get("hit_rate", 0)

print(f"✅ 模型加载成功")
print(f"   历史命中率: {hit_rate:.2%}")
print()

# 特征列
FEATURES = list(weights.keys())

# 连接数据库
conn = sqlite3.connect(DATABASE)

# 加载预测日期的数据
print(f"📊 加载 {PREDICTION_DATE} 的特征数据...")
query = f"""
SELECT * FROM {FEATURE_TABLE}
WHERE DATE(snapshot_date) = DATE(?)
"""
pred_df = pd.read_sql_query(query, conn, params=(PREDICTION_DATE,))

# 加载基金名称
print(f"   加载基金名称...")
name_query = """
SELECT DISTINCT fund_code, fund_name
FROM rank_snapshots
WHERE fund_name IS NOT NULL
"""
name_df = pd.read_sql_query(name_query, conn)

# 合并基金名称
pred_df = pred_df.merge(name_df, on='fund_code', how='left')

print(f"   找到 {len(pred_df)} 只基金")

if len(pred_df) == 0:
    print("❌ 没有找到数据！")
    exit(1)

# 计算预测分数
print(f"\n🔮 计算预测分数...")
feature_matrix = pred_df[FEATURES].fillna(0).to_numpy()
weight_vector = np.array([weights[feat] for feat in FEATURES])
scores = feature_matrix.dot(weight_vector)

pred_df = pred_df.copy()
pred_df["prediction_score"] = scores

# 选出预测的前30只基金
predicted_top = pred_df.nlargest(TOP_K, "prediction_score")

print(f"\n" + "=" * 80)
print(f"🏆 预测2026年上半年表现最好的{TOP_K}只基金")
print("=" * 80)
print()

for i, (idx, row) in enumerate(predicted_top.iterrows(), 1):
    fund_name = row.get('fund_name', '未知')
    if pd.isna(fund_name) or fund_name == '':
        fund_name = '未知'
    print(f"{i:2d}. {row['fund_code']:8s} {fund_name:30s} (预测分数: {row['prediction_score']:.4f})")

# 保存到Excel - 只保留关键列
output_columns = ['fund_code', 'fund_name', 'prediction_score', 'ret_6m', 'ret_12m',
                  'risk_adj_return', 'morningstar_score']
output_df = predicted_top[output_columns].copy()
output_df.columns = ['基金代码', '基金名称', '预测分数', '6个月收益率', '12个月收益率',
                     '风险调整收益', '晨星评分']

output_file = f"output/prediction_2026_H1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
output_df.to_excel(output_file, index=False)

print(f"\n💾 预测结果已保存到: {output_file}")

print("\n" + "=" * 80)
print("💡 使用建议")
print("=" * 80)
print(f"✅ 这个模型在2025年下半年的命中率是 {hit_rate:.2%}")
print("✅ 建议关注上述30只基金在2026年上半年的表现")
print("⚠️  投资有风险，模型预测仅供参考")
print()

conn.close()

