# GitHub 仓库设置指南

本文档说明如何设置 GitHub 仓库的协作和分支保护规则。

---

## 第一步：推送代码到 GitHub

### 1.1 在 GitHub 上创建新仓库

1. 访问 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `fundseeker`
   - **Description**: `Chinese Mutual Fund Analysis Toolkit - 中国公募基金数据采集与分析工具`
   - **Visibility**: Public（公开）
   - **不要勾选**：
     - ❌ Add a README file
     - ❌ Add .gitignore
     - ❌ Choose a license
   （因为我们已经有这些文件了）

3. 点击 "Create repository"

### 1.2 推送本地代码

```bash
cd /Users/haitongsun/Documents/04.wocheng/999.opensource/fundseeker

# 添加远程仓库（替换 your-username 为你的 GitHub 用户名）
git remote add origin https://github.com/your-username/fundseeker.git

# 确认分支名为 main
git branch -M main

# 推送代码
git push -u origin main
```

---

## 第二步：设置分支保护规则

### 2.1 访问分支保护设置

1. 在 GitHub 仓库页面，点击 **Settings**（设置）
2. 在左侧菜单中，点击 **Branches**（分支）
3. 在 "Branch protection rules" 部分，点击 **Add rule**（添加规则）

### 2.2 配置保护规则

#### 基础设置

**Branch name pattern**（分支名称模式）:
```
main
```

#### 推荐的保护规则

勾选以下选项：

✅ **Require a pull request before merging**（合并前需要 Pull Request）
   - 这是最重要的设置，防止直接推送到 main 分支
   - 子选项：
     - ✅ **Require approvals**（需要审批）
       - Required number of approvals: `1`（至少 1 个人审批）
     - ✅ **Dismiss stale pull request approvals when new commits are pushed**
       （新提交时取消旧的审批）
     - ✅ **Require review from Code Owners**（需要代码所有者审批）
       （如果你设置了 CODEOWNERS 文件）

✅ **Require status checks to pass before merging**（合并前需要通过状态检查）
   - 如果你设置了 CI/CD（GitHub Actions），可以要求测试通过
   - 子选项：
     - ✅ **Require branches to be up to date before merging**
       （合并前分支必须是最新的）

✅ **Require conversation resolution before merging**
   （合并前需要解决所有讨论）

✅ **Require signed commits**（需要签名提交）
   - 可选，增强安全性

✅ **Require linear history**（需要线性历史）
   - 可选，保持提交历史清晰

✅ **Include administrators**（包括管理员）
   - **重要**：勾选此项，连你自己也不能直接推送到 main
   - 这样可以强制自己也走 PR 流程，保持代码质量

❌ **Allow force pushes**（允许强制推送）
   - **不要勾选**，防止覆盖历史

❌ **Allow deletions**（允许删除）
   - **不要勾选**，防止误删分支

### 2.3 保存规则

点击页面底部的 **Create**（创建）按钮。

---

## 第三步：邀请协作者

### 3.1 添加协作者

1. 在仓库页面，点击 **Settings**（设置）
2. 在左侧菜单中，点击 **Collaborators and teams**（协作者和团队）
3. 点击 **Add people**（添加人员）
4. 输入对方的 GitHub 用户名或邮箱
5. 选择权限级别：
   - **Read**（只读）：只能查看和克隆
   - **Triage**（分类）：可以管理 Issues 和 PR
   - **Write**（写入）：可以推送到非保护分支，创建 PR
   - **Maintain**（维护）：可以管理仓库设置（不推荐给外部贡献者）
   - **Admin**（管理员）：完全控制（只给信任的核心成员）

**推荐**：给普通协作者 **Write** 权限即可。

### 3.2 协作者接受邀请

1. 协作者会收到邮件通知
2. 点击邮件中的链接接受邀请
3. 接受后即可开始贡献

---

## 第四步：协作工作流程

### 4.1 协作者的工作流程

```bash
# 1. Fork 仓库（在 GitHub 网页上点击 Fork）

# 2. 克隆自己的 fork
git clone https://github.com/collaborator-username/fundseeker.git
cd fundseeker

# 3. 添加上游仓库
git remote add upstream https://github.com/your-username/fundseeker.git

# 4. 创建功能分支
git checkout -b feature/new-feature

# 5. 进行修改并提交
git add .
git commit -m "feat: add new feature"

# 6. 推送到自己的 fork
git push origin feature/new-feature

# 7. 在 GitHub 上创建 Pull Request
```

### 4.2 维护者的审核流程

1. 收到 PR 通知
2. 审核代码：
   - 检查代码质量
   - 测试功能
   - 提出修改建议
3. 批准或请求修改
4. 合并 PR（使用 "Squash and merge" 或 "Rebase and merge"）

---

## 第五步：设置 GitHub Actions（可选）

创建自动化测试，确保代码质量。

### 5.1 创建工作流文件

创建 `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        cd fundseeker
        pip install -r requirements.txt

    - name: Run tests
      run: |
        cd fundseeker
        python -m unittest discover tests
```

这样每次有 PR 时，都会自动运行测试。

---

## 常见问题

### Q1: 我是管理员，但无法推送到 main 分支？

A: 这是正常的！如果你勾选了 "Include administrators"，连管理员也必须通过 PR。这是最佳实践。

**解决方法**：
1. 创建新分支
2. 提交修改
3. 创建 PR
4. 审核并合并

### Q2: 如何临时禁用分支保护？

A:
1. Settings → Branches
2. 找到 main 分支的规则
3. 点击 "Edit"
4. 取消勾选需要的规则
5. 完成操作后记得重新启用！

### Q3: 协作者说无法推送？

A: 检查：
1. 协作者是否接受了邀请？
2. 协作者是否在推送到自己的 fork？（正确）
3. 协作者是否在尝试直接推送到 main？（错误，应该创建 PR）

### Q4: 如何设置代码所有者？

A: 创建 `.github/CODEOWNERS` 文件：

```
# 所有文件的默认所有者
* @your-username

# fundseeker 目录
/fundseeker/ @your-username @collaborator1

# fund_reco_fit 目录
/fund_reco_fit/ @your-username @collaborator2

# 文档
/doc/ @your-username
```

---

## 推荐的仓库设置

### General（常规）

- ✅ **Issues**（启用 Issues）
- ✅ **Discussions**（启用讨论，可选）
- ❌ **Wikis**（禁用 Wiki，使用 doc/ 目录）
- ❌ **Projects**（禁用项目，除非需要）

### Pull Requests

- ✅ **Allow squash merging**（允许压缩合并）
- ✅ **Allow rebase merging**（允许变基合并）
- ❌ **Allow merge commits**（禁用合并提交，保持历史清晰）
- ✅ **Automatically delete head branches**（自动删除已合并的分支）

---

## 总结

完成以上设置后，你的仓库将：

✅ main 分支受到保护，无法直接推送
✅ 所有修改必须通过 Pull Request
✅ PR 需要至少 1 个人审批
✅ 协作者可以 fork 并提交 PR
✅ 代码质量得到保证

**下一步**：
1. 推送代码到 GitHub
2. 设置分支保护规则
3. 邀请协作者
4. 开始协作开发！
