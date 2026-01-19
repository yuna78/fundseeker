# 贡献指南 / Contributing Guide

感谢你对 FundSeeker 的关注！欢迎提交贡献。

Thank you for your interest in FundSeeker! Contributions are welcome.

---

## 如何贡献 / How to Contribute

### 1. Fork 仓库 / Fork the Repository

点击右上角的 "Fork" 按钮，将仓库 fork 到你的账号下。

Click the "Fork" button in the upper right corner to fork the repository to your account.

### 2. 克隆你的 Fork / Clone Your Fork

```bash
git clone https://github.com/your-username/fundseeker.git
cd fundseeker
```

### 3. 创建功能分支 / Create a Feature Branch

**重要**: 永远不要直接在 `main` 分支上工作！

**Important**: Never work directly on the `main` branch!

```bash
# 创建并切换到新分支
git checkout -b feature/your-feature-name

# 或者修复 bug
git checkout -b fix/bug-description
```

**分支命名规范 / Branch Naming Convention**:
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关

### 4. 进行修改 / Make Your Changes

- 遵循现有的代码风格
- 添加必要的注释
- 确保代码可以正常运行
- 如果添加新功能，请更新相关文档

Follow existing code style, add necessary comments, ensure code runs properly, and update documentation for new features.

### 5. 提交修改 / Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

**提交信息规范 / Commit Message Convention**:
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

### 6. 推送到你的 Fork / Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request / Create a Pull Request

1. 访问你的 fork 页面
2. 点击 "Compare & pull request" 按钮
3. 填写 PR 描述：
   - 说明你做了什么改动
   - 为什么需要这个改动
   - 如何测试这个改动

Visit your fork page, click "Compare & pull request", and describe:
- What changes you made
- Why these changes are needed
- How to test the changes

---

## 代码规范 / Code Standards

### Python 代码风格 / Python Code Style

- 遵循 PEP 8 规范
- 使用 4 空格缩进（不使用 Tab）
- 函数和变量使用 snake_case
- 类名使用 PascalCase
- 添加类型注解（type hints）

Follow PEP 8, use 4-space indentation, snake_case for functions/variables, PascalCase for classes, and add type hints.

### 示例 / Example

```python
from typing import List, Optional
from pathlib import Path

def fetch_fund_data(fund_code: str, start_date: Optional[str] = None) -> List[dict]:
    """
    获取基金数据

    Args:
        fund_code: 基金代码（6位）
        start_date: 开始日期，格式 YYYY-MM-DD

    Returns:
        基金数据列表
    """
    # 实现代码
    pass
```

---

## 测试 / Testing

在提交 PR 之前，请确保：

Before submitting a PR, ensure:

1. **代码可以运行 / Code Runs**
   ```bash
   # fundseeker
   cd fundseeker
   ./fundseeker.sh

   # fund_reco_fit
   cd fund_reco_fit
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **运行测试 / Run Tests**
   ```bash
   cd fundseeker
   python -m unittest discover tests
   ```

3. **检查代码风格 / Check Code Style**
   ```bash
   # 如果安装了 flake8
   flake8 src/
   ```

---

## 报告问题 / Report Issues

使用 GitHub Issues 报告问题时，请提供：

When reporting issues via GitHub Issues, please provide:

1. **问题描述 / Issue Description**
   - 清晰描述遇到的问题
   - Clearly describe the problem

2. **复现步骤 / Steps to Reproduce**
   ```
   1. 运行命令 xxx
   2. 输入参数 yyy
   3. 看到错误 zzz
   ```

3. **预期行为 / Expected Behavior**
   - 你期望发生什么
   - What you expected to happen

4. **实际行为 / Actual Behavior**
   - 实际发生了什么
   - What actually happened

5. **环境信息 / Environment**
   - 操作系统：macOS / Linux / Windows
   - Python 版本：`python --version`
   - 项目版本：`git log -1 --oneline`

---

## Pull Request 审核流程 / PR Review Process

1. **自动检查 / Automated Checks**
   - 代码风格检查
   - 测试通过
   - 无冲突

2. **人工审核 / Manual Review**
   - 维护者会审核你的代码
   - 可能会提出修改建议
   - 请及时响应反馈

3. **合并 / Merge**
   - 审核通过后，维护者会合并你的 PR
   - 你的贡献会出现在项目中！

---

## 分支保护规则 / Branch Protection Rules

`main` 分支受到保护，不能直接推送。所有修改必须通过 Pull Request。

The `main` branch is protected and cannot be pushed to directly. All changes must go through Pull Requests.

**保护规则 / Protection Rules**:
- ✅ 需要 Pull Request 才能合并
- ✅ 需要至少 1 个审核批准
- ✅ 必须通过状态检查
- ✅ 分支必须是最新的
- ❌ 不允许强制推送
- ❌ 不允许删除分支

---

## 开发环境设置 / Development Setup

### fundseeker

```bash
cd fundseeker

# macOS/Linux
./fundseeker.sh

# Windows
fundseeker.bat
```

### fund_reco_fit

```bash
cd fund_reco_fit

# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

---

## 需要帮助？ / Need Help?

- 📖 阅读 [README.md](README.md)
- 📖 查看 [用户手册](fundseeker/user_manual.md)
- 💬 在 Issues 中提问
- 📧 联系维护者

Read the README, check the user manual, ask in Issues, or contact maintainers.

---

## 行为准则 / Code of Conduct

- 尊重所有贡献者
- 保持友好和专业
- 接受建设性批评
- 关注对项目最有利的事情

Be respectful, friendly, professional, accept constructive criticism, and focus on what's best for the project.

---

感谢你的贡献！🎉

Thank you for your contribution! 🎉
