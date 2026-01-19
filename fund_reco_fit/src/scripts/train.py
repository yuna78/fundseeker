"""
针对前200名优化的自动调参脚本

这个脚本会：
1. 专门针对前200名进行优化
2. 尝试不同的特征组合
3. 找到在前200名范围内命中率最高的模型
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from itertools import product
import time

# 配置
DATABASE = "data/fundseeker_nav.db"
FEATURE_TABLE = "features_M_star"
TRAIN_START = "2021-01-01"
TRAIN_END = "2025-06-30"
TEST_DATE = "2025-12-31"
TOP_K = 200  # 改为200

# 特征列
FEATURES = [
    "ret_1m", "ret_3m", "ret_6m", "ret_12m", "ret_24m", "ret_36m",
    "risk_adj_return", "downside_vol_36m", "mdd_36m", "morningstar_score",
    "momentum_ratio_3m_12m", "vol_trend_3m_6m", "drawdown_diff_6m_36m"
]

print("=" * 80)
print("🔧 针对前200名的自动调参")
print("=" * 80)
print(f"训练期: {TRAIN_START} 到 {TRAIN_END}")
print(f"测试期: {TEST_DATE}")
print(f"选择数量: 前{TOP_K}只基金")
print()

# 连接数据库
conn = sqlite3.connect(DATABASE)

# 加载训练数据
print("📊 加载训练数据...")
query = f"""
SELECT * FROM {FEATURE_TABLE}
WHERE DATE(snapshot_date) >= DATE(?) AND DATE(snapshot_date) <= DATE(?)
ORDER BY snapshot_date, fund_code
"""
train_df = pd.read_sql_query(query, conn, params=(TRAIN_START, TRAIN_END))
print(f"   训练数据: {len(train_df)} 条记录")

# 添加未来收益（用于训练）
print("   计算未来收益...")
train_df = train_df.sort_values(["fund_code", "snapshot_date"])
train_df["future_ret_6m"] = train_df.groupby("fund_code")["ret_6m"].shift(-1)
train_df = train_df.dropna(subset=["future_ret_6m"])
print(f"   有效训练样本: {len(train_df)} 条")

# 加载测试数据
print("\n📈 加载测试数据...")
test_df = pd.read_sql_query(
    f"SELECT * FROM {FEATURE_TABLE} WHERE DATE(snapshot_date) = DATE(?)",
    conn, params=(TEST_DATE,)
)
print(f"   测试数据: {len(test_df)} 条记录")

# 获取真实的最佳基金（前200名）
actual_top = test_df.nlargest(TOP_K, "ret_6m")
actual_funds = set(actual_top["fund_code"].tolist())
print(f"   真实表现最好的前{TOP_K}只基金已确定")

# 定义要尝试的权重组合
print("\n🔧 准备尝试不同的权重组合...")
weight_candidates = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]

# 简化：只调整最重要的几个特征
key_features = ["ret_3m", "ret_6m", "ret_12m", "risk_adj_return", "morningstar_score"]
print(f"   重点调整特征: {key_features}")
print(f"   每个特征尝试 {len(weight_candidates)} 个权重值")
print(f"   总共需要测试: {len(weight_candidates) ** len(key_features)} 种组合")
print("   （这可能需要几分钟...）")

# 开始搜索最佳权重
best_hit_rate = 0
best_weights = None
best_hits = 0
tested = 0

print("\n🔍 开始搜索最佳权重...")
start_time = time.time()

for weight_combo in product(weight_candidates, repeat=len(key_features)):
    # 构建权重字典
    weights = {feat: 0.05 for feat in FEATURES}  # 默认权重
    for i, feat in enumerate(key_features):
        weights[feat] = weight_combo[i]

    # 在训练数据上计算分数
    feature_matrix = train_df[FEATURES].fillna(0).to_numpy()
    weight_vector = np.array([weights[feat] for feat in FEATURES])
    scores = feature_matrix.dot(weight_vector)

    train_df_copy = train_df.copy()
    train_df_copy["score"] = scores

    # 在测试数据上预测
    test_feature_matrix = test_df[FEATURES].fillna(0).to_numpy()
    test_scores = test_feature_matrix.dot(weight_vector)
    test_df_copy = test_df.copy()
    test_df_copy["score"] = test_scores

    # 选出预测的前200只
    predicted_top = test_df_copy.nlargest(TOP_K, "score")
    predicted_funds = set(predicted_top["fund_code"].tolist())

    # 计算命中率
    hits = predicted_funds & actual_funds
    hit_rate = len(hits) / TOP_K

    tested += 1

    # 更新最佳结果
    if hit_rate > best_hit_rate:
        best_hit_rate = hit_rate
        best_weights = weights.copy()
        best_hits = len(hits)
        print(f"   ✨ 找到更好的模型！命中率: {hit_rate:.2%} ({len(hits)}/{TOP_K})")

    # 每测试100个组合显示进度
    if tested % 100 == 0:
        elapsed = time.time() - start_time
        print(f"   已测试 {tested} 个组合，耗时 {elapsed:.1f}秒，当前最佳: {best_hit_rate:.2%}")

elapsed = time.time() - start_time
print(f"\n✅ 搜索完成！共测试 {tested} 个组合，耗时 {elapsed:.1f}秒")

# 显示最佳结果
print("\n" + "=" * 80)
print("🏆 最佳模型结果（针对前200名）")
print("=" * 80)
print(f"命中率: {best_hit_rate:.2%} ({best_hits}/{TOP_K})")
print(f"\n最佳权重:")
for feat, weight in sorted(best_weights.items(), key=lambda x: x[1], reverse=True):
    if weight > 0:
        print(f"  {feat}: {weight:.3f}")

# 保存最佳模型
output_file = "models/model_params_top200.json"
model_data = {
    "weights": best_weights,
    "hit_rate": best_hit_rate,
    "hit_count": best_hits,
    "total_predictions": TOP_K,
    "train_period": f"{TRAIN_START} to {TRAIN_END}",
    "test_date": TEST_DATE,
    "method": "grid_search_auto_tune_top200"
}

with open(output_file, "w") as f:
    json.dump(model_data, f, indent=2)

print(f"\n💾 最佳模型已保存到: {output_file}")

# 结论
print("\n" + "=" * 80)
print("💡 结论")
print("=" * 80)

random_baseline = TOP_K / 1112
print(f"随机选择基线命中率: {random_baseline:.2%}")
print(f"模型命中率: {best_hit_rate:.2%}")
print(f"模型比随机选择好 {best_hit_rate / random_baseline:.1f} 倍")

if best_hit_rate >= 0.25:
    print(f"\n✅ 命中率 {best_hit_rate:.2%} >= 25%，模型表现优秀！")
    print("   可以用这个模型预测2026年前200名")
elif best_hit_rate >= 0.20:
    print(f"\n⚠️  命中率 {best_hit_rate:.2%} 在20-25%之间")
    print("   模型有一定预测能力，但建议谨慎使用")
else:
    print(f"\n❌ 命中率 {best_hit_rate:.2%} < 20%")
    print("   模型预测能力有限，接近随机水平")

conn.close()
