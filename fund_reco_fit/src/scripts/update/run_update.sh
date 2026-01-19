#!/bin/bash
# 自动执行增量更新的脚本

echo "======================================================================"
echo "开始批量下载NAV数据"
echo "======================================================================"
echo ""

# 批次1: 1只基金，从2025-12-19开始
echo "批次 1/8: 1只基金，从2025-12-19开始"
cp batch_update_20251219.csv ../fundseeker/data/fund_list.csv
cd ../fundseeker
./fundseeker.sh nav --start-date 2025-12-19
cd ../fund_reco_fit

# 批次2: 5只基金，从2025-12-25开始
echo ""
echo "批次 2/8: 5只基金，从2025-12-25开始"
cp batch_update_20251225.csv ../fundseeker/data/fund_list.csv
cd ../fundseeker
./fundseeker.sh nav --start-date 2025-12-25
cd ../fund_reco_fit
