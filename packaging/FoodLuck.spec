# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller specification for the FoodLuck macOS application bundle."""

import re
from pathlib import Path

PROJECT_ROOT = Path.cwd().resolve()
VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (PROJECT_ROOT / "foodluck" / "__init__.py").read_text(encoding="utf-8"),
).group(1)

datas = [
    (str(PROJECT_ROOT / "foodluck" / "ui" / "assets"), "foodluck/ui/assets"),
]
hiddenimports = [
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
]

a = Analysis(
    [str(PROJECT_ROOT / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "numpy",
        "pandas",
        "matplotlib",
        "scipy",
        "pytest",
        "IPython",
        "PIL",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FoodLuck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(PROJECT_ROOT / "packaging" / "FoodLuck.icns"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FoodLuck",
)

app = BUNDLE(
    coll,
    name="FoodLuck.app",
    icon=str(PROJECT_ROOT / "packaging" / "FoodLuck.icns"),
    bundle_identifier="com.foodluck.desktop",
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "食运 FoodLuck",
        "CFBundleName": "FoodLuck",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": "2",
        "LSMinimumSystemVersion": "13.0",
        "LSApplicationCategoryType": "public.app-category.food-and-drink",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": (
            "FoodLuck 0.2. Restaurant data © OpenStreetMap contributors (ODbL)."
        ),
    },
)
