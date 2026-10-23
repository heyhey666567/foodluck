"""Application shell and dependency wiring for FoodLuck."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from foodluck import __version__
from foodluck.storage.database import Database
from foodluck.storage.paths import default_database_path
from foodluck.ui.main_window import MainWindow
from foodluck.ui.theme import ACCENT_INK, ACCENT, apply_theme


def make_app_icon() -> QIcon:
    """Draw a tiny branded icon at runtime; no binary assets required."""

    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(ACCENT))
    painter.drawRoundedRect(4, 4, 120, 120, 30, 30)
    painter.setPen(QColor(ACCENT_INK))
    font = QFont("PingFang SC", 64)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "食")
    painter.end()
    return QIcon(pixmap)


def build_application(argv=None) -> QApplication:
    """Create the QApplication and apply app-wide settings."""

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("FoodLuck")
    app.setApplicationDisplayName("食运 FoodLuck")
    app.setOrganizationName("FoodLuck")
    app.setApplicationVersion(__version__)
    apply_theme(app)
    app.setWindowIcon(make_app_icon())
    return app


def main() -> int:
    app = build_application()
    try:
        database = Database(default_database_path())
        database.initialize()
    except Exception as exc:  # pragma: no cover - startup failure path
        QMessageBox.critical(
            None,
            "食运无法启动",
            "本地数据库初始化失败。\n\n"
            f"{exc}\n\n"
            "请检查磁盘权限，或删除 FoodLuck 的应用数据目录后重试。",
        )
        return 1

    window = MainWindow(database)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
