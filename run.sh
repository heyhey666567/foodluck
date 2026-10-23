#!/usr/bin/env bash
# Launch FoodLuck from the project root.
set -euo pipefail

cd "$(dirname "$0")"

if [[ -n "${PYTHON:-}" ]]; then
    exec "$PYTHON" -m foodluck "$@"
fi

# Prefer a project virtualenv, then any local Python with PySide6 installed.
CANDIDATES=(
    ".venv/bin/python"
    "python3.14"
    "python3.13"
    "python3.12"
    "python3.11"
    "python3.10"
    "python3"
    "/opt/anaconda3/bin/python"
    "${HOME}/anaconda3/bin/python"
    "${HOME}/miniconda3/bin/python"
)

for candidate in "${CANDIDATES[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import PySide6" >/dev/null 2>&1; then
            exec "$candidate" -m foodluck "$@"
        fi
    fi
done

cat >&2 <<'EOF'
没有找到安装 PySide6 的 Python（需要 3.10+）。

请先安装依赖：
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

或者指定解释器：
  PYTHON=/path/to/python ./run.sh
EOF
exit 1
