#!/usr/bin/env python3
"""Generate a macOS .icns icon for FoodLuck without binary source art."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
ICONSET = ROOT / "FoodLuck.iconset"
ICNS = ROOT / "FoodLuck.icns"
MASTER = ROOT / "FoodLuck-1024.png"


def render_master() -> QImage:
    size = 1024
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    outer = QRectF(32, 32, size - 64, size - 64)
    gradient = QLinearGradient(outer.topLeft(), outer.bottomRight())
    gradient.setColorAt(0.0, QColor("#FFD08A"))
    gradient.setColorAt(0.55, QColor("#FFB454"))
    gradient.setColorAt(1.0, QColor("#F0773B"))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(outer, 235, 235)

    # Soft inner highlight so the icon reads well on both light and dark docks.
    painter.setBrush(QColor(255, 255, 255, 35))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(78, 72, size - 156, size - 300), 190, 190)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(255, 236, 198, 110), 5))
    painter.drawRoundedRect(QRectF(54, 54, size - 108, size - 108), 215, 215)

    font = QFont("PingFang SC", 520)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#2A1805"))
    painter.drawText(QRectF(0, -8, size, size), Qt.AlignCenter, "食")
    painter.end()
    return image


def main() -> int:
    QApplication(sys.argv)
    master_image = render_master()
    master_image.save(str(MASTER), "PNG")
    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    ICONSET.mkdir(parents=True)

    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, edge in sizes.items():
        scaled = master_image.scaled(
            edge,
            edge,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        scaled.save(str(ICONSET / filename), "PNG")

    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)],
        check=True,
    )
    print("Generated {}".format(ICNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
