# 增量更新基金数据 Skill

## 功能说明

这个skill用于增量更新基金数据，包括：
1. 从天天基金网API获取最新净值数据
2. 导入数据到SQLite数据库
3. 重新计算特征
4. 重新训练模型
5. 生成新的预测结果

## 使用方法

### 1. 更新所有基金数据（完整流程）
```
/update-fund-data --mode full
```

### 2. 只更新NAV数据（不重新训练）
```
/update-fund-data --mode nav-only
```

### 3. 只重新训练模型（使用现有数据）
```
/update-fund-data --mode retrain-only
```

### 4. 指定日期范围更新
```
/update-fund-data --start-date 2026-01-01 --end-date 2026-01-31
```

## 执行步骤

当用户调用这个skill时，你需要按照以下步骤执行：

### 步骤1：运行智能检查脚本

首先运行smart_update.py检查每只基金的数据状态：

```bash
cd fund_reco_fit
.venv/bin/python smart_update.py
```

这个脚本会：
- 检查每只基金的最新NAV日期
- 按最新日期分组统计需要更新的基金
- 自动生成批次更新文件（batch_update_YYYYMMDD.csv）
- 显示详细的更新计划

向用户报告检查结果，询问是否继续更新。

### 步骤2：批量下载NAV数据

smart_update.py会生成多个批次文件，每个批次对应一个起始日期。按照脚本输出的命令依次执行：

```bash
cd ../fundseeker
./fundseeker.sh nav --input ../fund_reco_fit/batch_update_20251227.csv --start-date 2025-12-27
./fundseeker.sh nav --input ../fund_reco_fit/batch_update_20260117.csv --start-date 2026-01-17
# ... 其他批次
```

**重要提示**：
- 每个批次会下载该组基金从指定日期到今天的所有数据
- 建议从最早的日期开始执行
- 每个批次完成后检查是否有错误

### 步骤3：导入NAV数据到数据库

使用import_data_simple.py导入新下载的数据：

```bash
cd ../fund_reco_fit
.venv/bin/python import_data_simple.py
```

这会将新的NAV数据导入到SQLite数据库。

### 步骤4：重新计算特征

运行feature_builder.py重新计算所有特征：

```bash
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star
```

这会基于最新的NAV数据重新计算所有基金的特征。

### 步骤5：重新训练模型

运行auto_tune_top200.py重新训练模型：

```bash
.venv/bin/python auto_tune_top200.py
```

这会使用最新的特征数据重新训练模型，找到最优权重。

### 步骤6：生成新的预测结果

运行predict_2026.py生成新的预测：

```bash
.venv/bin/python predict_2026.py
```

这会生成最新的Top 500基金推荐清单。

### 步骤7：报告更新结果

向用户报告更新完成情况，包括：
- 新增NAV数据记录数
- 更新的基金数量
- 新的特征记录数
- 模型命中率变化
- 新预测文件路径

## 注意事项

1. **数据完整性检查**：每个步骤完成后，检查数据是否正确导入
2. **错误处理**：如果某个步骤失败，向用户报告错误并询问是否继续
3. **备份建议**：建议用户在更新前备份数据库文件
4. **时间估算**：完整流程可能需要30-60分钟，取决于数据量

## 快速参考

### 检查数据状态命令
```bash
# 检查NAV数据最新日期
sqlite3 fund_reco_fit/data/fundseeker_nav.db "SELECT MAX(date) as latest_nav FROM nav_prices"

# 检查特征数据最新日期
sqlite3 fund_reco_fit/data/fundseeker_nav.db "SELECT MAX(snapshot_date) as latest_feature FROM features_M_star"

# 统计NAV记录数
sqlite3 fund_reco_fit/data/fundseeker_nav.db "SELECT COUNT(*) as total_records FROM nav_prices"

# 统计基金数量
sqlite3 fund_reco_fit/data/fundseeker_nav.db "SELECT COUNT(DISTINCT fund_code) as total_funds FROM nav_prices"
```

## 示例对话

### 示例1：完整更新流程

**用户**: /update-fund-data --mode full

**助手**:
```
正在检查当前数据状态...

📊 当前数据状态：
- NAV数据最新日期: 2026-01-16
- 特征数据最新日期: 2026-01-31
- 总NAV记录数: 5,916,054
- 基金数量: 4,702

是否继续更新数据？这将下载2026-01-17至今天的所有基金净值数据。
```

**用户**: 是

**助手**:
```
✅ 步骤1/6: 开始下载NAV数据...
[执行下载命令]
✅ 步骤2/6: 导入NAV数据到数据库...
[执行导入命令]
...
```

