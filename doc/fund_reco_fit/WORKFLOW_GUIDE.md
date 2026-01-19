# 工作流程指南 - 重组前后对比

**创建日期**: 2026-01-19
**目的**: 确保项目重组后，所有日常工作流程不受影响

---

## 📋 目录

1. [当前工作流程（重组前）](#当前工作流程重组前)
2. [重组后工作流程](#重组后工作流程)
3. [完整使用手册](#完整使用手册)
4. [常见问题](#常见问题)

---

## 当前工作流程（重组前）

### 工作流程1: 增量更新数据

**当前命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 步骤1: 检查哪些基金需要更新
.venv/bin/python check_fund_dates.py

# 步骤2: 生成批量更新文件
.venv/bin/python smart_update.py

# 步骤3: 下载新数据（使用fundseeker）
cd ../fundseeker
cp ../fund_reco_fit/batch_update_YYYYMMDD.csv data/fund_list.csv
./fundseeker.sh nav --start-date YYYY-MM-DD

# 步骤4: 导入数据到数据库
cd ../fund_reco_fit
.venv/bin/python import_data_simple.py

# 步骤5: 重新计算特征
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star
```

### 工作流程2: 训练模型

**当前命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 训练模型（网格搜索优化）
.venv/bin/python auto_tune_top200.py
```

**输出**: `models/model_params_top200.json`

### 工作流程3: 生成预测

**当前命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 生成Top 200预测
.venv/bin/python predict_2026.py
```

**输出**: `output/prediction_2026_H1_YYYYMMDD_HHMMSS.xlsx`

---

## 重组后工作流程

### 工作流程1: 增量更新数据

**重组后命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 步骤1: 检查哪些基金需要更新
.venv/bin/python src/scripts/update/check_dates.py

# 步骤2: 生成批量更新文件
.venv/bin/python src/scripts/update/smart_update.py

# 步骤3: 下载新数据（使用fundseeker）
cd ../fundseeker
cp ../fund_reco_fit/batch_update_YYYYMMDD.csv data/fund_list.csv
./fundseeker.sh nav --start-date YYYY-MM-DD

# 步骤4: 导入数据到数据库
cd ../fund_reco_fit
.venv/bin/python src/scripts/import_data.py

# 步骤5: 重新计算特征
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star
```

**变化**:
- ✅ `check_fund_dates.py` → `src/scripts/update/check_dates.py`
- ✅ `smart_update.py` → `src/scripts/update/smart_update.py`
- ✅ `import_data_simple.py` → `src/scripts/import_data.py`

### 工作流程2: 训练模型

**重组后命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 训练模型（网格搜索优化）
.venv/bin/python src/scripts/train.py
```

**变化**:
- ✅ `auto_tune_top200.py` → `src/scripts/train.py`

**输出**: 不变，仍然是 `models/model_params_top200.json`

### 工作流程3: 生成预测

**重组后命令**:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 生成Top 200预测
.venv/bin/python src/scripts/predict.py
```

**变化**:
- ✅ `predict_2026.py` → `src/scripts/predict.py`

**输出**: 不变，仍然是 `output/prediction_2026_H1_YYYYMMDD_HHMMSS.xlsx`

---

## 完整使用手册

### 场景1: 每周/每月数据更新

**目的**: 更新所有基金的最新净值数据

**步骤**:

#### 重组前（当前）:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 1. 检查数据状态
.venv/bin/python check_fund_dates.py

# 2. 生成更新计划
.venv/bin/python smart_update.py

# 3. 下载数据（针对每个批次）
cd ../fundseeker
cp ../fund_reco_fit/batch_update_20260117.csv data/fund_list.csv
./fundseeker.sh nav --start-date 2026-01-17

# 4. 导入数据
cd ../fund_reco_fit
.venv/bin/python import_data_simple.py

# 5. 重新计算特征
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star
```

#### 重组后:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 1. 检查数据状态
.venv/bin/python src/scripts/update/check_dates.py

# 2. 生成更新计划
.venv/bin/python src/scripts/update/smart_update.py

# 3. 下载数据（针对每个批次）
cd ../fundseeker
cp ../fund_reco_fit/batch_update_20260117.csv data/fund_list.csv
./fundseeker.sh nav --start-date 2026-01-17

# 4. 导入数据
cd ../fund_reco_fit
.venv/bin/python src/scripts/import_data.py

# 5. 重新计算特征
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star
```

**预期输出**:
- 批量更新CSV文件: `batch_update_YYYYMMDD.csv`
- 数据库更新: `data/fundseeker_nav.db`
- 特征文件: `data/features_M.parquet`

---

### 场景2: 训练新模型

**目的**: 使用最新数据训练模型，优化预测准确率

**步骤**:

#### 重组前（当前）:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 训练模型（测试16,807种参数组合）
.venv/bin/python auto_tune_top200.py
```

#### 重组后:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 训练模型（测试16,807种参数组合）
.venv/bin/python src/scripts/train.py
```

**预期输出**:
- 模型参数文件: `models/model_params_top200.json`
- 命中率报告: 显示在终端（如: 81.00%）

**耗时**: 约5-10分钟

---

### 场景3: 生成基金推荐

**目的**: 生成2026年上半年Top 200基金预测

**步骤**:

#### 重组前（当前）:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 生成预测
.venv/bin/python predict_2026.py
```

#### 重组后:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 生成预测
.venv/bin/python src/scripts/predict.py
```

**预期输出**:
- Excel文件: `output/prediction_2026_H1_YYYYMMDD_HHMMSS.xlsx`
- 包含200只基金的预测分数和排名

**耗时**: 约10-30秒


---

### 场景4: 完整的月度工作流程

**目的**: 每月更新数据、训练模型、生成新预测

#### 重组前（当前）:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 步骤1: 增量更新数据
.venv/bin/python check_fund_dates.py
.venv/bin/python smart_update.py
# ... 下载数据 ...
.venv/bin/python import_data_simple.py
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star

# 步骤2: 训练模型
.venv/bin/python auto_tune_top200.py

# 步骤3: 生成预测
.venv/bin/python predict_2026.py
```

#### 重组后:
```bash
cd /path/to/fundseeker/fund_reco_fit

# 步骤1: 增量更新数据
.venv/bin/python src/scripts/update/check_dates.py
.venv/bin/python src/scripts/update/smart_update.py
# ... 下载数据 ...
.venv/bin/python src/scripts/import_data.py
.venv/bin/python src/feature_builder.py --freq M --table-name features_M_star

# 步骤2: 训练模型
.venv/bin/python src/scripts/train.py

# 步骤3: 生成预测
.venv/bin/python src/scripts/predict.py
```

**总耗时**: 约3-4小时（主要是数据下载）

---

## 常见问题

### Q1: 重组后脚本会不会找不到文件？

**A**: 不会。脚本内部使用的是相对路径或动态路径，移动后仍然能正确找到数据文件。

**验证方法**:
```bash
# 重组后测试每个脚本
cd /path/to/fundseeker/fund_reco_fit
.venv/bin/python src/scripts/train.py --help
.venv/bin/python src/scripts/predict.py --help
```

### Q2: 如果重组后出问题怎么办？

**A**: 所有文件都有备份，可以立即恢复。

**回滚方法**:
```bash
# 方法1: 从备份恢复
cd /path/to/fundseeker
tar -xzf fundseeker_backup_YYYYMMDD_HHMMSS.tar.gz

# 方法2: 手动移回原位置
cd fund_reco_fit
mv src/scripts/train.py auto_tune_top200.py
mv src/scripts/predict.py predict_2026.py
# ... 其他文件 ...
```

### Q3: 重组会影响已有的模型和数据吗？

**A**: 不会。重组只是移动脚本文件，不会触碰：
- ✅ `data/fundseeker_nav.db` - 数据库文件
- ✅ `models/model_params_top200.json` - 模型参数
- ✅ `output/` - 所有输出文件
- ✅ `data/features_M.parquet` - 特征文件

### Q4: 重组后需要重新训练模型吗？

**A**: 不需要。现有的模型文件 `models/model_params_top200.json` 仍然有效，可以直接使用。


### Q5: 批量更新CSV文件会保存在哪里？

**A**: 重组后，批量更新CSV文件仍然会生成在 `fund_reco_fit/` 根目录下。

**重组前**: `batch_update_20260117.csv`（根目录）
**重组后**: `batch_update_20260117.csv`（根目录，位置不变）

这些文件会被自动归档到 `_archived/batch_updates/`，但不影响使用。

---

## 快速参考卡

### 核心命令对照表

| 功能 | 重组前 | 重组后 |
|------|--------|--------|
| 检查数据状态 | `check_fund_dates.py` | `src/scripts/update/check_dates.py` |
| 生成更新计划 | `smart_update.py` | `src/scripts/update/smart_update.py` |
| 导入数据 | `import_data_simple.py` | `src/scripts/import_data.py` |
| 训练模型 | `auto_tune_top200.py` | `src/scripts/train.py` |
| 生成预测 | `predict_2026.py` | `src/scripts/predict.py` |

### 数据文件位置（不变）

| 文件类型 | 位置 | 说明 |
|---------|------|------|
| 数据库 | `data/fundseeker_nav.db` | 不变 |
| 特征文件 | `data/features_M.parquet` | 不变 |
| 模型参数 | `models/model_params_top200.json` | 不变 |
| 预测输出 | `output/prediction_*.xlsx` | 不变 |
| 批量更新CSV | `batch_update_*.csv` | 不变（根目录） |

---

## 重组验证清单

重组完成后，请执行以下验证：

```bash
cd /path/to/fundseeker/fund_reco_fit

# 1. 检查目录结构
ls -la src/scripts/
ls -la src/scripts/update/
ls -la _archived/

# 2. 测试核心脚本
.venv/bin/python src/scripts/train.py --help
.venv/bin/python src/scripts/predict.py --help
.venv/bin/python src/scripts/import_data.py --help

# 3. 验证数据文件完整性
ls -lh data/fundseeker_nav.db
ls -lh models/model_params_top200.json
ls -lh data/features_M.parquet

# 4. 检查Git状态
git status
git check-ignore _archived/
```

**预期结果**:
- ✅ 所有脚本都能正常运行（或显示帮助信息）
- ✅ 数据文件都存在且大小正常
- ✅ `_archived/` 目录被Git忽略

---

## 总结

### 重组的核心变化

**只有3个变化**:
1. 脚本位置从根目录移到 `src/scripts/`
2. 部分脚本重命名（更专业的命名）
3. 临时文件归档到 `_archived/`（不提交到Git）

### 不变的内容

**所有重要的东西都不变**:
- ✅ 数据库文件
- ✅ 模型参数
- ✅ 特征文件
- ✅ 输出目录
- ✅ 脚本功能和逻辑

### 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 脚本路径错误 | 🟢 低 | 脚本使用相对路径，自动适配 |
| 数据丢失 | 🟢 零 | 只移动脚本，不触碰数据 |
| 无法回滚 | 🟢 零 | 有完整备份，可随时恢复 |
| 影响工作流程 | 🟡 低 | 只需更新命令路径 |

---

## 下一步

如果您确认理解了重组前后的变化，我们可以：

1. **立即执行重组**（推荐）
   - 创建备份
   - 执行重组
   - 验证功能

2. **先测试一个脚本**（保守）
   - 只移动一个脚本测试
   - 确认无问题后再移动其他

3. **暂缓执行**
   - 继续使用当前结构
   - 等待更合适的时机

**您的选择**: _______________

