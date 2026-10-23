#!/usr/bin/env bash
# Build an ad-hoc-signed macOS .app and a distributable zip.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -n "${PYTHON:-}" ]]; then
    PY="$PYTHON"
elif [[ -x ".build-venv/bin/python" ]]; then
    PY=".build-venv/bin/python"
else
    PY="python3"
fi

if ! "$PY" -c "import PyInstaller, PySide6" >/dev/null 2>&1; then
    echo "需要 PyInstaller 和 PySide6。建议："
    echo "  python3 -m venv --system-site-packages .build-venv"
    echo "  .build-venv/bin/pip install pyinstaller"
    exit 1
fi

VERSION="$("$PY" -c 'from foodluck import __version__; print(__version__)')"
ARCH="$(uname -m)"
ARTIFACT="FoodLuck-${VERSION}-macOS-${ARCH}.zip"

echo "==> Generating icon"
"$PY" packaging/generate_icon.py

echo "==> Cleaning build output"
rm -rf build dist

echo "==> Building FoodLuck.app with PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean packaging/FoodLuck.spec

if [[ ! -d "dist/FoodLuck.app" ]]; then
    echo "Build did not produce dist/FoodLuck.app" >&2
    exit 1
fi

echo "==> Signing ad hoc"
codesign --force --deep --sign - "dist/FoodLuck.app"
codesign --verify --deep --strict "dist/FoodLuck.app"

echo "==> Creating zip"
ditto -c -k --keepParent "dist/FoodLuck.app" "dist/${ARTIFACT}"

echo "==> Writing checksum"
(
    cd dist
    shasum -a 256 "$ARTIFACT" > "${ARTIFACT}.sha256"
)

echo
echo "Built:"
echo "  dist/FoodLuck.app"
echo "  dist/${ARTIFACT}"
echo "  dist/${ARTIFACT}.sha256"
du -sh "dist/FoodLuck.app" "dist/${ARTIFACT}"
