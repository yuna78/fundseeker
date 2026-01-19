#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENTRYPOINT="$PROJECT_ROOT/.main.py"

if [ ! -d "$VENV_DIR" ]; then
  echo "🔧 正在创建虚拟环境..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [ ! -f "$VENV_DIR/.deps-installed" ] || [ requirements.txt -nt "$VENV_DIR/.deps-installed" ]; then
  echo "📦 安装依赖..."
  pip install -q -r "$PROJECT_ROOT/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
  touch "$VENV_DIR/.deps-installed"
fi

echo "🚀 运行 FundSeeker CLI..."
if [ $# -eq 0 ]; then
  python "$ENTRYPOINT" menu
else
  python "$ENTRYPOINT" "$@"
fi
