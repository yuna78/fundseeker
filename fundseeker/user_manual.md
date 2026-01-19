# FundSeeker CLI 使用指南（小白友好版）

本指南帮助你在终端中使用 FundSeeker CLI，完成基金排行抓取、详情补充、净值下载和进度查看。无需编程基础，只需按步骤操作即可。

---

## 0. 准备环境
1. 打开终端（Terminal）。
2. 进入项目目录：
   ```bash
   cd /Users/haitongsun/Documents/04.wocheng/999.fundseeker
   ```
3. **一键启动脚本（推荐）**  
   - macOS / Linux：项目自带 `fundseeker.sh`，会自动创建虚拟环境并安装依赖。直接运行：
     ```bash
     ./fundseeker.sh
     ```
   - Windows：使用命令提示符（cmd）或 PowerShell 运行：
   ```bat
   fundseeker.bat
   ```
   会出现一个菜单（1 初始化环境、2 排行+评级、3 详情抓取、4 帮助、5 查看进度、0 退出），按照提示输入数字即可。  
   如果你想跳过菜单直接执行某个命令，也可以加参数，例如：
   ```bash
   ./fundseeker.sh rank        # macOS / Linux
   ./fundseeker.sh details
   ```
   ```bat
   fundseeker.bat rank         # Windows
   fundseeker.bat details
   ```
   如果脚本提示缺少依赖，可以单独运行：
   ```bat
   fundseeker.bat repair
   ```
   这会重新安装依赖后退出，再重新执行 `fundseeker.bat` 即可。
   > 如果你更熟悉传统方式，也可自行 `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`。

> **提示**：下文示例若使用 `./fundseeker.sh ...`，Windows 用户只需换成 `fundseeker.bat ...` 即可。

---

## 1. 查看帮助
```bash
./fundseeker.sh --help
```
可以看到支持的命令：`rank`、`details`、`progress`、`menu`。

> 如果执行 `./fundseeker.sh`（不带参数）会自动进入菜单：  
> 1. 初始化环境  
> 2. 获取基金排行并补充评级  
> 3. 根据基金清单抓取详情  
> 4. 生成推荐列表  
> 5. 查看帮助/说明  
> 6. 查看进度  
> 7. 下载基金历史净值  
> 0. 退出

---

## 2. 抓取基金排行 + 评级
```bash
./fundseeker.sh rank
```
可选参数：
- `--start-date 2024-01-01`
- `--end-date 2024-12-31`
- `--limit 1000`（只导出前 1000 条，可根据需要调整）

执行后，程序会从天天基金抓取 10,000 条排行数据并附上评级。结果文件会自动保存到 `output/rank_with_rating_<时间>.xlsx`。
终端会提示保存路径，日志记录在隐藏目录 `.fs/logs/<当天日期>/rank.log`。

> 在菜单中选择“2. 获取基金排行并补充评级”时，系统会提示输入“要导出的前 N 条记录”；留空即可导出全部。

---

## 3. 根据基金列表抓取详情
### 3.1 准备基金列表
1. 打开 `templates/fund_list_template.csv`，复制到你自己的文件（支持 CSV 或 Excel）。
2. 至少保留列 `基金代码`（6 位数字），可选列 `基金简称`、备注等。
3. 将文件放在项目目录或任意路径下，记住路径。

### 3.2 运行命令
项目已为你准备好固定的输入文件 `data/fund_list.csv`：
1. 双击打开 `data/fund_list.csv`（或用 Excel / Numbers）。
2. 按模板填写你筛选后的基金代码，可以直接覆盖示例行。
3. 保存后，直接运行：
   ```bash
   ./fundseeker.sh details
   ```
   若你确实想使用别的文件，再通过 `--input 其他文件路径` 指定。

提示：
- 默认支持断点续传。如果想重新开始，加 `--no-resume`。
- 如果找不到 `data/fund_list.csv`，脚本会提示你先创建/替换该文件。

### 3.3 输出
- 结果 Excel：`output/fund_details_<时间>.xlsx`
- 进度 JSON：`.fs/progress/details_<日期时间>.json`
- 日志：`.fs/logs/<当天日期>/details.log`

程序会在终端显示当前处理到第几个基金，可以按 `Ctrl+C` 中断，稍后再次运行会从进度文件继续。


## 4. 下载基金历史净值
当你需要晨星式回测或自行计算收益/风险指标时，可以直接下载净值：

```bash
./fundseeker.sh nav --start-date 2023-01-01 --end-date 2025-12-31
```

默认会读取 `data/fund_list.csv` 中列出的所有基金，逐个拉取净值并保存到 `output/nav/nav_基金代码.xlsx`（再次运行会覆盖）。  
如果只想下载某一只基金，可指定基金代码：

```bash
./fundseeker.sh nav 000001 --start-date 2023-01-01 --end-date 2025-12-31 --fmt csv
```

说明：
- `--start-date`/`--end-date` 可选，格式 `YYYY-MM-DD`，留空表示接口返回的全部历史记录。
- `--fmt` 支持 `excel`（默认，对应 `.xlsx`）或 `csv`。

在菜单模式下选择“7. 批量下载净值”，系统只会询问日期和格式，默认使用 `data/fund_list.csv`。

---

## 5. 生成推荐列表
当排行与详情数据准备好后，可以运行：
```bash
./fundseeker.sh recommend
```
或带参数：
```bash
./fundseeker.sh recommend --top-n 20
```
程序会在 `output/` 目录生成 `recommendations_<时间>.csv`，并在终端展示推荐值最高的前若干条。

---

## 6. 高级推荐模式
如果你已经在 `fund_reco_fit` 跑完“净值导入→特征构建→因子优化”，并在 `config.yaml` 中配置了 `advanced_model`（指向 SQLite 和模型权重），就可以使用高级推荐：

```bash
./fundseeker.sh recommend --mode advanced --top-n 200
```

提示：
- 该模式会读取 `fund_reco_fit/data/fundseeker_nav.db` 里的特征表（默认 `features_M`）和 `models/model_params.json` 中的权重。
- 输出文件名为 `output/recommendations_advanced_<时间>.xlsx`，列中会带上预测得分以及关键特征。
- 在菜单选择“4. 生成推荐列表”时，系统会提示你选择模式（1=基础八因子，2=高级模型）。

若未配置 `advanced_model` 或数据库/权重文件缺失，命令会提示你先按 `fund_reco_fit` 文档完成数据准备。

---

## 7. 查看进度
```bash
./fundseeker.sh progress
```
默认显示最新日期的进度文件，也可以指定日期：
```bash
./fundseeker.sh progress --date 2025-12-09
```
输出内容包括：输入文件、输出文件、处理数量、完成百分比、最后更新时间等。`--date` 只是按文件名包含的日期过滤，留空会显示所有进度。


## 8. 交互式菜单（可选）
如果你想通过菜单操作，可以执行：
```bash
./fundseeker.sh menu
```
终端会出现：
```
1. 初始化环境
2. 获取基金排行并补充评级
3. 根据基金清单抓取详情
4. 生成推荐列表
5. 查看帮助/说明
6. 查看进度
7. 批量下载净值（data/fund_list.csv）
0. 退出
```
输入对应数字即可执行功能。

---

## 9. 常见问题
1. **提示缺少依赖 / ModuleNotFoundError**  
   确认已激活虚拟环境，并执行过 `pip install -r requirements.txt`。

2. **抓取失败（网络问题）**  
   可能是网络不通或接口限制，稍后再试。日志可在 `.fs/logs/<日期>/...` 中查看详情。

3. **模板校验失败**  
   详情功能要求至少包含 `基金代码` 列。可直接复制 `templates/fund_list_template.csv` 作为模板。

4. **输出文件找不到**  
所有结果都直接存放在 `output/` 目录（大多数文件名含时间戳，`output/nav/nav_基金代码` 会覆盖式更新）。终端输出中也会提示完整路径。

---

## 10. 退出与清理
完成操作后，可在终端输入：
```bash
deactivate
```
退出虚拟环境。

---

如有任何问题，可查看 `doc/requirements.md`、`doc/design.md`、`doc/test_cases.md`、`doc/plan.md` 获取更多技术细节，也欢迎继续提问。祝使用顺利！ 🙌
