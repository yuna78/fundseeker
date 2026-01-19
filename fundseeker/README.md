# FundSeeker CLI

统一的终端入口，帮你用最少的命令完成基金排行、详情补录与智能推荐：

- 抓取天天基金排行，并附带多家机构评级，可在菜单中输入要导出的前 N 条；
- 根据筛选后的基金列表批量补充基金详情、基金经理、任职表现，支持断点续传；
- 可随时拉取任意基金的历史净值时间序列，供回测或自定义分析；
- 将排行与详情合并后，依据配置化的 8 项指标生成推荐值（默认输出前 200 条，并带上各项得分）；
- 所有产出集中在 `output/`，进度和日志放在隐藏目录 `.fs/`，保持根目录干净。

## 快速开始

macOS/Linux：
```bash
./fundseeker.sh               # 启动交互式菜单（推荐的方式）
./fundseeker.sh rank          # 直接运行排行+评级，可配合 --limit
./fundseeker.sh details       # 使用 data/fund_list.csv 抓取详情
./fundseeker.sh nav           # 批量下载 data/fund_list.csv 中所有基金的净值
./fundseeker.sh nav 000001    # 只下载基金 000001 的历史净值（可配 start/end）
./fundseeker.sh recommend     # 基于最新数据输出推荐结果（默认基础八因子）
./fundseeker.sh recommend --mode advanced  # 使用 fund_reco_fit 训练的高级模型
```

Windows：
```bat
fundseeker.bat               # 启动菜单：1 初始化 / 2 排行 / 3 详情 / 4 推荐 / 5 帮助 / 6 进度 / 7 净值
fundseeker.bat rank          # 直接运行排行+评级
fundseeker.bat details       # 使用 data/fund_list.csv 抓取详情
fundseeker.bat nav           # 批量下载 data/fund_list.csv 中的基金净值
fundseeker.bat nav 000001    # 下载基金 000001 的历史净值
fundseeker.bat recommend     # 输出推荐 Excel（默认前 200 条）
fundseeker.bat repair        # 重新安装/修复依赖（遇到缺包或网络问题时运行）
```
> 两个脚本均默认使用清华 PyPI 镜像加速 `pip install`，若需要可在脚本内修改。

> 若想手动控制，可 `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` 后使用 `python .main.py ...`。

主要命令：

| 命令 | 说明 |
|------|------|
| `python .main.py init` | 初始化目录与默认基金列表（一般由脚本自动完成） |
| `python .main.py rank` | 抓取基金排行+评级，可通过 `--start-date`/`--end-date` 指定区间，`--limit N` 仅导出前 N 条 |
| `python .main.py details --input path/to/list.xlsx` | 根据基金列表抓取详情（CSV/Excel 均可）；默认自动续传，可加 `--no-resume` 禁用 |
| `python .main.py nav [FUND_CODE] --start-date YYYY-MM-DD --end-date YYYY-MM-DD --fmt excel/csv` | 留空 FUND_CODE 时批量读取 `data/fund_list.csv` 并下载所有基金；若提供 FUND_CODE 则只拉取该基金 |
| `python .main.py progress --date YYYY-MM-DD` | 查看指定日期的进度，若不传日期则显示最新目录 |
| `python .main.py recommend --top-n 200 [--mode advanced]` | 默认输出基础八因子结果；指定 `--mode advanced` 则读取 SQLite 特征 + 模型权重生成高级推荐 |
| `python .main.py menu` | 启动交互式菜单 |

所有结果文件都会直接写入 `output/`（文件名带时间戳，例如 `rank_with_rating_20251214_132415.xlsx`、`recommendations_20251214_143011.xlsx`）。进度与日志藏在 `.fs/` 里，避免干扰日常操作：

- `output/`：排行、详情、推荐等 Excel 结果。
- `output/nav/`：通过 `nav` 命令导出的净值时间序列（文件名 `nav_基金代码.xlsx/csv`，重复运行会覆盖）。
- `.fs/progress/`：断点续传使用的 JSON 进度。
- `.fs/logs/<YYYY-MM-DD>/...`：日志文件夹，默认无需查看。

### 推荐权重配置

`src/services/recommend_service.py` 会自动合并最近一次的排行 (`rank_with_rating_*.xlsx`) 与详情 (`fund_details_*.xlsx`) 文件，计算以下 8 个评分维度，并输出带有 `推荐值`、`评级得分` 等列的 Excel：

1. 近期动量得分（收益/波动的组合）
2. 中期趋势得分
3. 长期稳定性得分
4. 风险惩罚（波动 proxy）
5. 基金经理得分（任职回报 * 任职年限）
6. 规模流动性得分
7. 机构评级得分（多家机构评分取平均，再缩放）
8. 基金年龄得分

在 `config.yaml` 的 `recommendation_weights` 节点可调整权重，示例：

```yaml
recommendation_weights:
  recent: 0.35
  mid: 0.20
  long: 0.15
  risk_penalty: 0.10
  manager: 0.10
  scale: 0.05
  rating: 0.03
  age: 0.02
```

也可使用环境变量 `FUNDSEEKER_RECENT_WEIGHT` 等覆盖，实现不同策略下的推荐模型。

### 高级推荐（可选）

如果你在 `fund_reco_fit` 目录内已经运行了 NAV 导入、特征构建、因子优化（生成 `data/fundseeker_nav.db` 与 `models/model_params.json`），即可在 `config.yaml` 中配置：

```yaml
advanced_model:
  - label: 6m
    db_path: ../fund_reco_fit/data/fundseeker_nav.db
    feature_table: features_M_star
    weights_path: ../fund_reco_fit/models/model_params_6m.json
    top_k: 200
  - label: 12m
    db_path: ../fund_reco_fit/data/fundseeker_nav.db
    feature_table: features_M_star
    weights_path: ../fund_reco_fit/models/model_params_12m.json
    top_k: 200
```

此时运行 `./fundseeker.sh recommend --mode advanced --adv-variant 6m` 或 `--adv-variant 12m`（默认为列表里的第一项）即可在不同训练目标之间切换。新版特征表会自动过滤掉净值历史少于 36 个月的基金，并写入晨星风格的风险调整指标（36M 年化收益、下行波动、最大回撤、风险调整收益、同类型百分位等），推荐输出也会附带这些列及 `预测得分`。

基金列表模板位于 `templates/fund_list_template.csv`。系统默认使用 `data/fund_list.csv` 作为输入文件，你只需在运行详情功能前打开该文件（或复制模板内容）并填入自己的基金列表。

## 测试

基础单元测试位于 `tests/`，可通过以下方式运行：

```bash
python -m unittest discover tests
```

更多需求、设计、测试用例、推荐业务逻辑与实施计划请参见 `doc/requirements.md`、`doc/design.md`、`doc/recommendation_business_design.md`、`doc/test_cases.md` 与 `doc/plan.md`。
