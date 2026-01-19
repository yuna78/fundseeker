#!/bin/bash
# 简单的基金数据更新脚本

echo "=================================="
echo "基金数据更新脚本"
echo "=================================="

# 1. 转换Excel为CSV
echo ""
echo "步骤 1: 转换基金清单为CSV格式..."
python3 << 'EOF'
import pandas as pd

# 读取Excel文件（请修改为你的实际路径）
df = pd.read_excel('../fundseeker/data/fund_list.xlsx')

# 格式化基金代码为6位
df['基金代码'] = df['基金'].astype(str).str.zfill(6)

# 保存为CSV
output_file = '../fundseeker/data/fund_list.csv'
df[['基金代码', '基金简称']].to_csv(output_file, index=False)

print(f"✅ 已保存到: {output_file}")
print(f"   总共 {len(df)} 只基金")
EOF

# 2. 使用fundseeker获取数据
echo ""
echo "步骤 2: 使用fundseeker获取基金数据..."
echo "⏳ 这可能需要较长时间，请耐心等待..."
cd ../fundseeker
.venv/bin/python .main.py nav --start-date 2021-01-01

# 3. 导入数据到数据库
echo ""
echo "步骤 3: 导入数据到数据库..."
cd ../fund_reco_fit
python3 src/nav_importer.py run

echo ""
echo "=================================="
echo "✅ 更新完成！"
echo "=================================="
