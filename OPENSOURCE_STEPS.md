# 开源操作完整指南

**日期**: 2026-01-19
**目标**: 将项目开源到GitHub

---

## ✅ 已准备好的内容

### 1. 文档
- ✅ README.md（双语，项目总览）
- ✅ CLAUDE.md（Claude指令）
- ✅ doc/ 目录（完整的文档结构）
- ✅ 用户手册和技术文档

### 2. 代码
- ✅ 代码结构清晰
- ✅ 脚本已整理到 src/scripts/
- ✅ 无私人路径信息

### 3. 配置
- ✅ .gitignore 已完善
- ✅ requirements.txt 已准备

---

## ❌ 还需要创建的文件

### 1. LICENSE 文件（必需）
### 2. CONTRIBUTING.md（推荐）
### 3. .gitkeep 文件（保持空目录结构）

---

## 📋 开源步骤（推荐方案）

### 方案：创建新目录，初始化新Git仓库

这是最干净的方式，可以完全控制提交历史。

---

## 🚀 详细操作步骤

### 步骤1: 创建必需文件

#### 1.1 创建 LICENSE 文件

```bash
cd /Users/haitongsun/Documents/04.wocheng/999.fundseeker

cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 FundSeeker Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

#### 1.2 创建 CONTRIBUTING.md（可选但推荐）

```bash
cat > CONTRIBUTING.md << 'EOF'
# 贡献指南

感谢你对 FundSeeker 的关注！

## 如何贡献

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 代码规范

- 遵循 PEP 8 Python 代码规范
- 添加必要的注释和文档
- 确保代码可以正常运行

## 报告问题

请使用 GitHub Issues 报告问题，并提供：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（操作系统、Python版本等）

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-username/fundseeker.git
cd fundseeker

# 设置 fundseeker
cd fundseeker
./fundseeker.sh  # macOS/Linux
# 或
fundseeker.bat   # Windows

# 设置 fund_reco_fit
cd ../fund_reco_fit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
EOF
```

---

### 步骤2: 创建 .gitkeep 文件（保持空目录）

```bash
# 创建空目录的占位文件
touch fundseeker/data/.gitkeep
touch fundseeker/output/.gitkeep
touch fund_reco_fit/data/.gitkeep
touch fund_reco_fit/models/.gitkeep
touch fund_reco_fit/output/.gitkeep
```

---

### 步骤3: 创建新的开源目录

```bash
# 在你想要的位置创建新目录
cd ~/Documents
mkdir fundseeker-opensource
cd fundseeker-opensource
```

---

### 步骤4: 复制文件到新目录

```bash
# 复制所有需要的文件（排除不需要的）
rsync -av --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='.fs' \
  --exclude='output' \
  --exclude='data/*.csv' \
  --exclude='data/*.xlsx' \
  --exclude='data/*.db' \
  --exclude='*.log' \
  --exclude='doc/archive' \
  --exclude='*_backup_*.tar.gz' \
  /Users/haitongsun/Documents/04.wocheng/999.fundseeker/ \
  ./
```

**说明**: 这个命令会复制所有文件，但排除：
- Git历史（.git）
- 虚拟环境（.venv）
- Python缓存（__pycache__）
- 数据文件（.csv, .xlsx, .db）
- 输出目录（output）
- 归档文档（doc/archive）
- 备份文件

---

### 步骤5: 初始化新的Git仓库

```bash
# 进入新目录
cd ~/Documents/fundseeker-opensource

# 初始化Git仓库
git init

# 添加所有文件
git add .

# 查看将要提交的文件
git status
```

---

### 步骤6: 创建首次提交

```bash
# 创建首次提交
git commit -m "Initial commit: FundSeeker - Chinese Mutual Fund Analysis Toolkit

- Complete data collection pipeline from Eastmoney
- Basic 8-factor recommendation system
- Advanced ML-based recommendation with feature engineering
- Comprehensive documentation (English + Chinese)
- Cross-platform support (macOS, Linux, Windows)"
```

---
