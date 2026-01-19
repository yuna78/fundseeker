# FundSeeker

[English](#english) | [中文](#中文)

---

## English

### Overview

**FundSeeker** is a comprehensive Python-based toolkit for Chinese mutual fund analysis and recommendation. It provides end-to-end capabilities from data collection to intelligent fund recommendations using both rule-based and machine learning approaches.

### Key Features

- **Data Collection**: Fetch fund rankings, ratings, detailed information, and historical NAV data from Eastmoney (天天基金网)
- **Multi-Agency Ratings**: Aggregate ratings from Morningstar, Shanghai Securities, and other agencies
- **Basic Recommendations**: 8-factor scoring system with configurable weights
- **Advanced ML Models**: Feature engineering and backtesting using SQLite + trained models
- **Batch Processing**: Resume-capable batch operations for large datasets (10,000+ funds)
- **Cross-Platform**: Works on macOS, Linux, and Windows

### Project Structure

```
fundseeker/
├── fundseeker/          # Core CLI tool for data fetching and basic recommendations
│   ├── src/            # Service layer, data fetchers, utilities
│   ├── templates/      # CSV templates for fund lists
│   └── README.md       # Detailed CLI documentation
│
└── fund_reco_fit/      # Advanced recommendation pipeline
    ├── src/            # NAV importer, feature builder, optimizer, backtester
    ├── doc/            # Design docs and validation guides
    └── README.md       # Advanced features documentation
```

### Quick Start

#### 1. Clone the Repository

```bash
git clone https://github.com/yuna78/999.fundseeker.git
cd fundseeker
```

#### 2. Run FundSeeker CLI

**macOS/Linux:**
```bash
cd fundseeker
./fundseeker.sh        # Launch interactive menu
```

**Windows:**
```bash
cd fundseeker
fundseeker.bat         # Launch interactive menu
```

The shell scripts will automatically:
- Create a Python virtual environment
- Install dependencies
- Launch the interactive menu

#### 3. Basic Workflow

**Step 1: Fetch Fund Rankings**
```bash
./fundseeker.sh rank --limit 200
```
This fetches top 200 funds with multi-agency ratings.

**Step 2: Fetch Fund Details**
```bash
./fundseeker.sh details --input data/fund_list.csv
```
Fetches detailed information (manager, scale, inception date) for funds in your list.

**Step 3: Generate Recommendations**
```bash
./fundseeker.sh recommend --top-n 200
```
Generates recommendations using the 8-factor scoring model.

### Complete Workflow: Data → Model → Recommendations

#### Phase 1: Data Collection (fundseeker/)

1. **Fetch rankings and ratings**:
   ```bash
   cd fundseeker
   ./fundseeker.sh rank --limit 1000
   ```

2. **Download historical NAV data**:
   ```bash
   ./fundseeker.sh nav
   ```
   This downloads NAV time series for all funds in `data/fund_list.csv`.

3. **Fetch fund details**:
   ```bash
   ./fundseeker.sh details
   ```

All outputs are saved to `fundseeker/output/` with timestamps.

#### Phase 2: Feature Engineering & Model Training (fund_reco_fit/)

1. **Import NAV data into SQLite**:
   ```bash
   cd ../fund_reco_fit
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt

   python3 -m src.nav_importer \
     --fundseeker-output ../fundseeker/output \
     --database data/fundseeker_nav.db
   ```

2. **Build features**:
   ```bash
   python3 -m src.feature_builder \
     --database data/fundseeker_nav.db \
     --freq M \
     --table-name features_M_star
   ```
   This computes 36-month rolling metrics (returns, volatility, drawdowns, Morningstar-style risk metrics).

3. **Train factor model**:
   ```bash
   python3 -m src.optimizer \
     --database data/fundseeker_nav.db \
     --feature-table features_M_star \
     --snapshot-start 2020-01-01 \
     --snapshot-end 2024-12-31 \
     --future-horizon 6 \
     --top-k 200 \
     --output-json models/model_params_6m.json
   ```

4. **Validate model** (optional but recommended):
   ```bash
   ./quick_validate.sh
   ```
   Choose walk-forward validation or real 2025 data validation to check for overfitting.

#### Phase 3: Generate Advanced Recommendations (fundseeker/)

1. **Configure advanced model** in `fundseeker/config.yaml`:
   ```yaml
   advanced_model:
     - label: 6m
       db_path: ../fund_reco_fit/data/fundseeker_nav.db
       feature_table: features_M_star
       weights_path: ../fund_reco_fit/models/model_params_6m.json
       top_k: 200
   ```

2. **Generate recommendations**:
   ```bash
   cd ../fundseeker
   ./fundseeker.sh recommend --mode advanced --adv-variant 6m
   ```

The output Excel file includes predicted scores, Morningstar-style risk metrics, and rankings.

### Configuration

#### Basic Recommendation Weights

Edit `fundseeker/config.yaml`:

```yaml
recommendation_weights:
  recent: 0.35        # Recent momentum
  mid: 0.20           # Mid-term trend
  long: 0.15          # Long-term stability
  risk_penalty: 0.10  # Volatility penalty
  manager: 0.10       # Manager performance
  scale: 0.05         # Fund size
  rating: 0.30        # Agency ratings
  age: 0.02           # Fund age
```

Or use environment variables:
```bash
export FUNDSEEKER_RECENT_WEIGHT=0.4
export FUNDSEEKER_RATING_WEIGHT=0.25
```

### Documentation

- **FundSeeker CLI**: See `fundseeker/README.md` for detailed command reference
- **Advanced Features**: See `fund_reco_fit/README.md` for ML pipeline documentation
- **Design Docs**: See `fundseeker/doc/` and `fund_reco_fit/doc/` for architecture and design decisions

### Requirements

- Python 3.8+
- Dependencies are automatically installed by shell scripts
- Core libraries: pandas, requests, typer, openpyxl, PyYAML

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 中文

### 项目简介

**FundSeeker** 是一个全面的中国公募基金分析和推荐工具包。它提供从数据采集到智能推荐的端到端能力，支持基于规则和机器学习的推荐方法。

### 核心功能

- **数据采集**：从天天基金网抓取基金排行、评级、详细信息和历史净值数据
- **多机构评级**：汇总晨星、上海证券等多家机构的评级
- **基础推荐**：8因子评分系统，权重可配置
- **高级机器学习模型**：基于SQLite的特征工程和回测
- **批量处理**：支持断点续传的批量操作（可处理10,000+基金）
- **跨平台**：支持macOS、Linux和Windows

### 项目结构

```
fundseeker/
├── fundseeker/          # 核心CLI工具，用于数据抓取和基础推荐
│   ├── src/            # 服务层、数据抓取器、工具类
│   ├── templates/      # 基金列表CSV模板
│   └── README.md       # 详细的CLI文档
│
└── fund_reco_fit/      # 高级推荐流水线
    ├── src/            # NAV导入器、特征构建器、优化器、回测器
    ├── doc/            # 设计文档和验证指南
    └── README.md       # 高级功能文档
```

### 快速开始

#### 1. 克隆仓库

```bash
git clone https://github.com/yuna78/999.fundseeker.git
cd fundseeker
```

#### 2. 运行 FundSeeker CLI

**macOS/Linux:**
```bash
cd fundseeker
./fundseeker.sh        # 启动交互式菜单
```

**Windows:**
```bash
cd fundseeker
fundseeker.bat         # 启动交互式菜单
```

Shell脚本会自动：
- 创建Python虚拟环境
- 安装依赖
- 启动交互式菜单

#### 3. 基础工作流

**步骤1：抓取基金排行**
```bash
./fundseeker.sh rank --limit 200
```
抓取前200只基金及多机构评级。

**步骤2：抓取基金详情**
```bash
./fundseeker.sh details --input data/fund_list.csv
```
抓取基金列表中的详细信息（基金经理、规模、成立日期等）。

**步骤3：生成推荐**
```bash
./fundseeker.sh recommend --top-n 200
```
使用8因子评分模型生成推荐。

### 完整工作流：数据 → 模型 → 推荐

#### 阶段1：数据采集 (fundseeker/)

1. **抓取排行和评级**：
   ```bash
   cd fundseeker
   ./fundseeker.sh rank --limit 1000
   ```

2. **下载历史净值数据**：
   ```bash
   ./fundseeker.sh nav
   ```
   为 `data/fund_list.csv` 中的所有基金下载净值时间序列。

3. **抓取基金详情**：
   ```bash
   ./fundseeker.sh details
   ```

所有输出保存到 `fundseeker/output/`，文件名带时间戳。

#### 阶段2：特征工程和模型训练 (fund_reco_fit/)

1. **导入NAV数据到SQLite**：
   ```bash
   cd ../fund_reco_fit
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt

   python3 -m src.nav_importer \
     --fundseeker-output ../fundseeker/output \
     --database data/fundseeker_nav.db
   ```

2. **构建特征**：
   ```bash
   python3 -m src.feature_builder \
     --database data/fundseeker_nav.db \
     --freq M \
     --table-name features_M_star
   ```
   计算36个月滚动指标（收益、波动、回撤、晨星风格风险指标）。

3. **训练因子模型**：
   ```bash
   python3 -m src.optimizer \
     --database data/fundseeker_nav.db \
     --feature-table features_M_star \
     --snapshot-start 2020-01-01 \
     --snapshot-end 2024-12-31 \
     --future-horizon 6 \
     --top-k 200 \
     --output-json models/model_params_6m.json
   ```

4. **验证模型**（可选但推荐）：
   ```bash
   ./quick_validate.sh
   ```
   选择滚动窗口验证或2025年真实数据验证，检查过拟合问题。

#### 阶段3：生成高级推荐 (fundseeker/)

1. **在 `fundseeker/config.yaml` 中配置高级模型**：
   ```yaml
   advanced_model:
     - label: 6m
       db_path: ../fund_reco_fit/data/fundseeker_nav.db
       feature_table: features_M_star
       weights_path: ../fund_reco_fit/models/model_params_6m.json
       top_k: 200
   ```

2. **生成推荐**：
   ```bash
   cd ../fundseeker
   ./fundseeker.sh recommend --mode advanced --adv-variant 6m
   ```

输出的Excel文件包含预测得分、晨星风格风险指标和排名。

### 配置

#### 基础推荐权重

编辑 `fundseeker/config.yaml`：

```yaml
recommendation_weights:
  recent: 0.35        # 近期动量
  mid: 0.20           # 中期趋势
  long: 0.15          # 长期稳定性
  risk_penalty: 0.10  # 波动惩罚
  manager: 0.10       # 基金经理表现
  scale: 0.05         # 基金规模
  rating: 0.30        # 机构评级
  age: 0.02           # 基金年龄
```

或使用环境变量：
```bash
export FUNDSEEKER_RECENT_WEIGHT=0.4
export FUNDSEEKER_RATING_WEIGHT=0.25
```

### 文档

- **FundSeeker CLI**：查看 `fundseeker/README.md` 了解详细命令参考
- **高级功能**：查看 `fund_reco_fit/README.md` 了解机器学习流水线文档
- **设计文档**：查看 `fundseeker/doc/` 和 `fund_reco_fit/doc/` 了解架构和设计决策

### 系统要求

- Python 3.8+
- 依赖会由shell脚本自动安装
- 核心库：pandas、requests、typer、openpyxl、PyYAML

### 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

### 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。
