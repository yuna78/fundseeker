# Advanced NAV-Based Recommendation Design

## 1. Goal
利用已经可以批量下载的历史净值，构建一套“更贴近机构量化选基流程”的推荐引擎：既要考虑收益，也要量化风险、超额收益与风格暴露，并且可通过 walk-forward 回测验证策略稳定性。

## 2. Overall Architecture

1. **Data Ingestion**
   - 来源：`fundseeker/output/nav/nav_<code>.xlsx`（覆盖式更新）、排行/详情 Excel。
   - 统一写入 `fund_reco_fit/data/fundseeker_nav.db`（SQLite）：
     - `nav_prices`：`fund_code, date, nav, nav_acc, return_daily`
     - `fund_meta`：基金类型、规模、经理、费率（来自详情）
     - `rank_snapshots`：排行+评级快照
   - SQLite 优点：嵌入式、易部署、支持 SQL/索引/增量刷新，可直接以 DuckDB/Polars 读取。

2. **Feature Engineering**
   - 基于 SQLite/Parquet 输出月度或周度频率的特征表（`features_<freq>`）：
     - **动量/趋势**：1/3/6/12 个月收益、相对强弱指标、MA 斜率。
     - **波动/风险**：标准差、下行偏差、最大回撤、Calmar、Sortino。
     - **超额收益**：相对基准指数的 alpha、beta、R²。
     - **基金属性**：规模、成立年限、经理任期表现、申购赎回状态、评级等。
   - 统一保存为 Parquet，方便 backtest/ML。

3. **Modeling / Recommendation Engine**
   - **因子权重法（Baseline）**：
     - 采用线性组合：`Score = Σ w_i * Factor_i`，权重通过网格/贝叶斯在验证期最优化，目标函数可定义为“未来 N 月年化收益 - λ*最大回撤”。
     - 作为与现有推荐值的融合版本，便于快速上线。
   - **机器学习扩展**（可选）：
     - 使用 Elastic Net / Gradient Boosting / XGBoost 预测未来 3/6 个月收益或排名。
     - 模型输入：滚动窗口特征、基金属性、宏观指数（可从 SQLite 的附表加载）。
     - 输出：预测收益或胜率 → 排序 → 选 Top N。
   - **组合规则**：
     - 按基金类型设置容量限制（防止某类占满）。
     - 可选等权或风险均衡权重，方便与回测一致。

4. **Backtesting & Evaluation**
   - 依托 `fund_reco_fit/src/backtester.py` 升级版：
     - 从 SQLite 抽取训练/验证数据，支持 expanding/rolling。
     - 评估指标：累计收益、年化、夏普、最大回撤、命中率、信息比。
     - 记录最佳参数/模型版本（写回 `models/` 或 SQLite `model_meta` 表）。
   - 输出报告：`output/backtest_summary_*.csv`, `output/model_params.json`。

5. **Integration with FundSeeker CLI**
   - 推荐命令在生成推荐值前，先检查是否存在“高级模型输出”。若存在则加载最新参数/模型进行打分；否则回退到当前八因子。
   - 新增 `./fundseeker.sh recommend --mode advanced` 切换；默认仍使用稳健方案，待验证通过后再切换默认。
   - 提供 `fund_reco_fit` 内的 CLI（如 `python -m src.pipeline train`）自动从 SQLite 拉数据、训练、导出模型，再由 FundSeeker 读取。

## 3. Data Flow Detail

1. **NAV Importer** (`fund_reco_fit/src/nav_importer.py`)
   - 扫描 `fundseeker/output/nav/nav_*.xlsx` → 解析 → upsert 至 SQLite `nav_prices`。
   - 建立索引 `(fund_code, date)`，方便范围查询。

2. **Feature Builder** (`fund_reco_fit/src/feature_builder.py`)
   - 直接对 SQLite 执行 SQL 或用 Pandas/Polars 读取 → 计算 rolling 指标。
   - 输出 `features_YYYYMM.parquet` + 写入 SQLite `features` 表（主键 `fund_code, snapshot_date`）。

3. **Optimizer / Trainer** (`fund_reco_fit/src/optimizer.py`)
   - 输入：`features` + `future_return`（来自 nav/排行）。
   - 输出：权重向量或模型文件（Pickle/ONNX）。
   - 同步写入 `fund_reco_fit/models/model_<timestamp>.json`, `fund_reco_fit/models/model_<timestamp>.pkl`。

4. **Serving Layer**
   - FundSeeker CLI 读取最新模型/权重（可通过 `config.yaml` 指定路径）。
   - 推荐输出表新增列：`预测收益`, `最大回撤`, `模型版本` 等，方便解释。

## 4. Success Criteria
1. 数据链路：SQLite 中覆盖 95% 以上基金的近 3~5 年净值，特征表生成时间可控（< 5 分钟）。
2. 模型：在 walk-forward 回测中，Advanced 模式的年化/夏普等指标显著优于当前八因子基线。
3. CLI 集成：用户可通过菜单或 `./fundseeker.sh recommend --mode advanced` 直接获取新的推荐列表，输出包含可解释字段。

## 5. Next Steps
详见 `nav_recommendation_tasks.md`；优先完成数据落地 + 特征构建，再推进回测与模型调优，最后接入 CLI。
