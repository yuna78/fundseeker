# Fund Recommendation Lab

This workspace hosts the advanced recommendation pipeline (SQLite ingestion, feature engineering, backtesting, ML). Folder overview:

- `src/`: tooling (nav importer, feature builder, backtester, validation tools, etc.).
- `doc/`: design docs (`nav_recommendation_design.md`, `validation_guide.md`, etc.).
- `data/` (created at runtime): holds `fundseeker_nav.db`, Parquet features, etc.
- `requirements.txt`: minimal依赖（pandas/numpy/typer/openpyxl/pyarrow）供 `pip install -r requirements.txt`。

## 🆕 Model Validation System (NEW!)

**解决过拟合问题**：如果你的模型在历史数据上表现好，但预测2025年时命中率很低，请使用这个验证系统。

### 快速开始

```bash
cd fund_reco_fit
./quick_validate.sh
```

选择验证模式：
1. **Walk-Forward Validation**：测试模型在多个时间窗口的稳定性
2. **2025 Real Data Validation**：对比预测和2025年真实表现
3. **Both**：运行两种验证

详细说明请查看：
- **快速指南**：`doc/validation_summary.md`
- **完整文档**：`doc/validation_guide.md`

---

## NAV Importer (Step 1)

安装依赖：

```bash
cd fund_reco_fit
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

安装完依赖后，FundSeeker 下载完净值 (`output/nav/nav_*.xlsx`)、排行、详情文件，运行：

```bash
python3 -m src.nav_importer \
  --fundseeker-output ../fundseeker/output \
  --database data/fundseeker_nav.db
```
- 布尔选项默认开启，如需跳过可加 `--no-include-nav` / `--no-include-meta` / `--no-include-rank`。
- 若已激活虚拟环境，可直接用 `python`；Windows 需改为 `.\.venv\Scripts\python.exe`。

说明：
- `fundseeker-output` 默认指向 `../fundseeker/output`，可省略。
- `database` 默认写到 `data/fundseeker_nav.db`，首次会自动创建。
- `include-*` 开关控制导入的类型（净值 / 基金元数据 / 排行快照）。
- 净值文件名固定 `output/nav/nav_基金代码.xlsx/csv`（由 FundSeeker CLI 生成，重复下载会覆盖）。

导入完成后即可在 SQLite 中查询：

```bash
sqlite3 data/fundseeker_nav.db "SELECT fund_code, COUNT(*) FROM nav_prices GROUP BY fund_code LIMIT 5;"
```

后续步骤（特征构建、回测、先进推荐）详见 `doc/nav_recommendation_design.md` 与 `doc/nav_recommendation_tasks.md`。

## Feature Builder (Step 2)

在 SQLite 数据足够的前提下，生成月度特征表：

```bash
python3 -m src.feature_builder \
  --database data/fundseeker_nav.db \
  --freq M \
  --table-name features_M_star
```

- `freq` 支持 `M`（默认，月度）、`W`（周度）、`D`（日度，下游若需要更细粒度）。
- 只有拥有 ≥36 个月净值历史的基金才会被纳入（仿晨星规则，新基金不会生成特征）。
- 输出包含 1/3/6/12/24/36 月动量、36 月年化收益、36 月下行波动、36 月最大回撤、Morningstar 风格的风险调整收益 `risk_adj_return`、`morningstar_score` 与同类百分位 `morningstar_percentile`，并新增 `momentum_ratio_3m_12m`（动量衰减）、`vol_trend_3m_6m`（波动趋势）、`drawdown_diff_6m_36m`（回撤改善）等指标，帮助识别是否透支涨幅。
- 结果写入 SQLite（例：`features_M_star`）以及 Parquet/CSV（`data/features_M.parquet`，若缺少 `pyarrow` 会自动退回 CSV）。
- 若要保留旧表，可加 `--no-overwrite-table`，此时会执行 `INSERT`。
- 若环境未安装 `pyarrow`/`fastparquet`，脚本会自动退回 CSV 输出（同目录下 `.csv`）。

之后即可使用这些特征进行回测、因子优化或机器学习建模。

## Factor Optimizer (Step 3)

基于特征与未来收益，搜索一组较优的因子权重：

```bash
python3 -m src.optimizer \
  --database data/fundseeker_nav.db \
  --feature-table features_M_star \
  --snapshot-start 2020-01-01 \
  --snapshot-end 2024-12-31 \
  --top-k 200 \
  --grid "0.05,0.1" \
  --min-abs-weight 0.05 \
  --max-weight "ret_1m=0.1,ret_3m=0.1" \
  --future-horizon 6 \
  --output-json models/model_params.json
```

- 默认因子包括 `ret_1m/3m/6m/12m/24m/36m`、`risk_adj_return`、`downside_vol_36m`、`mdd_36m`、`morningstar_score`、动量衰减/波动趋势/回撤改善等字段，已覆盖短中长期收益与晨星式风险因子；你也可以修改 `src/optimizer.py` 中的 `FEATURE_COLS` 自定义。
- `grid` 决定候选权重集合，可按需求扩展；注意组合数 = grid^因子数。
- `min-abs-weight` 强制每个因子权重 ≥ 指定阈值，避免训练结果把某个因子压成 0。
- `max-weight` 可约束指定特征的权重上限（示例中把 `ret_1m`、`ret_3m` 压到 ≤0.10），用于降低模型对近期收益的依赖。
- `future-horizon` 控制训练时使用的“未来收益”窗口（默认 6 个月），可切换为 3 或 12 个月输出不同版本。
- `top-k` 表示每个 snapshot 取前 N 只基金计算组合收益与命中率。
- 输出 JSON 包含最优权重、年化收益、Sharpe、最大回撤、命中率等指标，便于后续回测或线上服务使用。

## Cross-Sectional Ridge Fit (Step 3b, optional)

如果你只想快速“校准”某一天的推荐结果，可直接用 2024-12-31 的特征去拟合 2025-12-31 的真实收益：

```bash
python3 -m src.crosssec_fit \
  --database data/fundseeker_nav.db \
  --feature-table features_M_star \
  --snapshot-train "2024-12-31 00:00:00" \
  --snapshot-target "2025-12-31 00:00:00" \
  --target-horizon 12 \
  --ridge-lambda 0.1 \
  --top-k 30 \
  --output-json models/model_params_crosssec12.json
```

脚本会输出命中率，并把新的权重写成 JSON，供 FundSeeker 通过 `--adv-variant crosssec12` 使用。可根据需要调整 `target-horizon`、`ridge-lambda` 或特征列表。

## Advanced Backtest (Step 4)

使用训练好的权重，评估某时间段的表现：

```bash
python3 -m src.backtester \
  --database data/fundseeker_nav.db \
  --feature-table features_M_star \
  --weights-json models/model_params.json \
  --snapshot-start 2023-01-01 \
  --snapshot-end 2023-12-31 \
  --top-k 30 \
  --output-csv output/advanced_backtest_2023.csv
```

脚本会输出年化收益、Sharpe、最大回撤、命中率，同时将逐期收益写入 CSV，方便继续绘制曲线或与基准比较。更换 `weights-json` 即可测试不同模型/参数。
