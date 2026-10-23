"""A small, dependency-free design system for the FoodLuck desktop app."""

from __future__ import annotations

import sys
from pathlib import Path


def _asset_directory() -> Path:
    """Find SVG assets in source checkouts and PyInstaller .app bundles."""

    candidates = [Path(__file__).resolve().parent / "assets"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.extend(
            [
                Path(meipass) / "foodluck" / "ui" / "assets",
                Path(meipass) / "assets",
            ]
        )
    executable = Path(sys.executable).resolve()
    for parent in executable.parents:
        candidates.extend(
            [
                parent / "Resources" / "foodluck" / "ui" / "assets",
                parent / "Resources" / "assets",
            ]
        )
    for candidate in candidates:
        if (candidate / "chevron-down.svg").is_file():
            return candidate
    return candidates[0]


_ASSET_DIR = _asset_directory()
_ARROW_ICON = (_ASSET_DIR / "chevron-down.svg").as_posix()
_CHECK_ICON = (_ASSET_DIR / "check.svg").as_posix()

# Palette: a warm "late-night kitchen" accent on a calm blue-black canvas.
BG = "#090D12"
SIDEBAR = "#0C1219"
SURFACE = "#111923"
SURFACE_RAISED = "#16212D"
SURFACE_SOFT = "#0F1720"
BORDER = "#22303F"
BORDER_SOFT = "#1A2633"
TEXT = "#F4F1EA"
TEXT_SOFT = "#C6CED6"
MUTED = "#8493A3"
ACCENT = "#FFB454"
ACCENT_STRONG = "#FF8A3D"
ACCENT_INK = "#2A1805"
MINT = "#5AD8AE"
DANGER = "#FF7A7A"

FONT_STACK = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Segoe UI", sans-serif'

APP_STYLE = f"""
* {{
    outline: none;
}}
QWidget {{
    color: {TEXT};
    font-family: {FONT_STACK};
    font-size: 13px;
}}
QMainWindow, QWidget#appRoot {{
    background-color: {BG};
}}
QWidget#page {{
    background-color: transparent;
}}
QFrame#sidebar {{
    background-color: {SIDEBAR};
    border-right: 1px solid {BORDER_SOFT};
}}
QFrame#card, QFrame#filterCard, QFrame#sideCard, QFrame#listCard,
QFrame#modeCard, QFrame#excludeCard, QFrame#tipCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 18px;
}}
QFrame#heroCard {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #18212A, stop:0.58 #121A23, stop:1 #1C1814);
    border: 1px solid #30404E;
    border-radius: 24px;
}}
QFrame#excludedRow, QFrame#historyRow, QFrame#favoriteRow {{
    background-color: {SURFACE_SOFT};
    border: 1px solid {BORDER_SOFT};
    border-radius: 14px;
}}
QFrame#sideNote {{
    background-color: #101821;
    border: 1px solid {BORDER_SOFT};
    border-radius: 13px;
}}
QLabel#sideNoteTitle {{
    color: {TEXT_SOFT};
    font-size: 11px;
    font-weight: 700;
}}
QLabel#navSection {{
    color: #5F6E7D;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel {{
    background: transparent;
}}
QLabel#brandName {{
    color: {TEXT};
    font-size: 25px;
    font-weight: 800;
}}
QLabel#brandCaption {{
    color: {MUTED};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel#logoMark {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_STRONG});
    color: {ACCENT_INK};
    border-radius: 15px;
    font-size: 25px;
    font-weight: 900;
}}
QLabel#pageTitle {{
    color: {TEXT};
    font-size: 30px;
    font-weight: 800;
}}
QLabel#pageSubtitle {{
    color: {MUTED};
    font-size: 13px;
}}
QLabel#sectionTitle {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#fieldLabel {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#helper {{
    color: {MUTED};
    font-size: 11px;
}}
QLabel#heroEyebrow {{
    color: {ACCENT};
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}}
QLabel#heroTitle {{
    color: {TEXT};
    font-size: 30px;
    font-weight: 800;
}}
QLabel#heroName {{
    color: {TEXT};
    font-size: 32px;
    font-weight: 800;
}}
QLabel#heroMeta {{
    color: {TEXT_SOFT};
    font-size: 13px;
}}
QLabel#heroAddress {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel#bigNumber {{
    color: {TEXT};
    font-size: 42px;
    font-weight: 800;
}}
QLabel#smallNumber {{
    color: {TEXT};
    font-size: 20px;
    font-weight: 750;
}}
QLabel#muted {{
    color: {MUTED};
    font-size: 12px;
}}
QLabel#soft {{
    color: {TEXT_SOFT};
    font-size: 12px;
}}
QLabel#badge {{
    background-color: #1B2733;
    border: 1px solid #2A3948;
    border-radius: 9px;
    color: {TEXT_SOFT};
    font-size: 10px;
    font-weight: 650;
    padding: 3px 9px;
}}
QLabel#badge[tone="accent"] {{
    background-color: #32250F;
    border-color: #6A4A18;
    color: {ACCENT};
}}
QLabel#badge[tone="mint"] {{
    background-color: #102A23;
    border-color: #1E5142;
    color: {MINT};
}}
QLabel#badge[tone="danger"] {{
    background-color: #2D1A1C;
    border-color: #5D2E33;
    color: {DANGER};
}}
QLabel#badge[tone="quiet"] {{
    background-color: transparent;
    border-color: {BORDER};
    color: {MUTED};
}}
QLabel#rowTitle {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#emptyIcon {{
    background-color: #171F28;
    border: 1px solid {BORDER};
    border-radius: 20px;
    color: {ACCENT};
    font-size: 24px;
    font-weight: 700;
}}
QLabel#emptyTitle {{
    color: {TEXT};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#toast {{
    color: {TEXT};
    background-color: #1D2935;
    border: 1px solid #3A4C5D;
    border-radius: 13px;
    padding: 9px 18px;
    font-size: 12px;
    font-weight: 650;
}}
QLineEdit, QComboBox, QDoubleSpinBox {{
    min-height: 38px;
    padding: 0 12px;
    color: {TEXT};
    background-color: {SURFACE_SOFT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_INK};
}}
QLineEdit:hover, QComboBox:hover, QDoubleSpinBox:hover {{
    border-color: #34485A;
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
    background-color: #121C26;
}}
QLineEdit::placeholder {{
    color: #637282;
}}
QComboBox {{
    padding-right: 28px;
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox::down-arrow {{
    image: url("{_ARROW_ICON}");
    width: 12px;
    height: 8px;
    margin-right: 11px;
}}
QComboBox QAbstractItemView {{
    color: {TEXT};
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 5px;
    selection-background-color: #29323B;
    selection-color: {ACCENT};
    outline: 0;
}}
QCheckBox {{
    color: {TEXT_SOFT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid #415263;
    background-color: {SURFACE_SOFT};
}}
QCheckBox::indicator:checked {{
    border-color: {ACCENT};
    background-color: {ACCENT};
    image: url("{_CHECK_ICON}");
}}
QPushButton {{
    border: none;
    border-radius: 10px;
    padding: 0 15px;
    min-height: 38px;
    color: {TEXT};
    background-color: transparent;
    font-weight: 650;
}}
QPushButton:hover {{
    background-color: #1B2734;
}}
QPushButton:pressed {{
    background-color: #223140;
}}
QPushButton:disabled {{
    color: #5E6B78;
}}
QPushButton#primary {{
    color: {ACCENT_INK};
    background-color: {ACCENT};
    min-height: 44px;
    padding: 0 24px;
    font-size: 14px;
    font-weight: 800;
}}
QPushButton#primary:hover {{
    background-color: #FFC16E;
}}
QPushButton#primary:pressed {{
    background-color: {ACCENT_STRONG};
}}
QPushButton#primary:disabled {{
    background-color: #3B3327;
    color: #897154;
}}
QPushButton#secondary {{
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    min-height: 42px;
}}
QPushButton#secondary:hover {{
    background-color: #1D2A38;
    border-color: #34485A;
}}
QPushButton#ghost {{
    color: {MUTED};
    border: 1px solid transparent;
    min-height: 38px;
}}
QPushButton#ghost:hover {{
    color: {TEXT};
    background-color: #16212C;
    border-color: {BORDER_SOFT};
}}
QPushButton#dangerGhost {{
    color: {DANGER};
    border: 1px solid #40262A;
    background-color: transparent;
}}
QPushButton#dangerGhost:hover {{
    background-color: #2A191C;
}}
QPushButton#nav {{
    color: {MUTED};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 0 14px;
    min-height: 42px;
    text-align: left;
    font-size: 13px;
    font-weight: 650;
}}
QPushButton#nav:hover {{
    color: {TEXT};
    background-color: #121B24;
}}
QPushButton#nav:checked {{
    color: {TEXT};
    background-color: #1A232D;
    border-color: #2A3948;
}}
QPushButton#modeButton {{
    color: {MUTED};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 34px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton#modeButton:hover {{
    color: {TEXT};
    background-color: #1A2531;
}}
QPushButton#modeButton:checked {{
    color: {ACCENT};
    background-color: #2B2418;
    border-color: #5C451F;
}}
QPushButton#sourceButton {{
    color: {MUTED};
    background-color: {SURFACE_SOFT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    min-height: 28px;
    padding: 0 11px;
    font-size: 11px;
    font-weight: 700;
}}
QPushButton#sourceButton:hover {{
    color: {TEXT};
    border-color: #3A4D5E;
}}
QPushButton#sourceButton:checked {{
    color: {ACCENT_INK};
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton#sourceButton:disabled {{
    color: #5E6B78;
    background-color: #101821;
    border-color: {BORDER_SOFT};
}}
QPushButton#coordinateButton {{
    color: {TEXT_SOFT};
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    border-radius: 9px;
    min-height: 38px;
    min-width: 52px;
    padding: 0 10px;
    font-size: 12px;
}}
QPushButton#coordinateButton:hover {{
    color: {ACCENT};
    border-color: #4D3A1D;
}}
QPushButton#manageButton {{
    color: {ACCENT};
    background-color: transparent;
    border: 1px solid #4D3A1D;
    border-radius: 9px;
    min-height: 32px;
    padding: 0 12px;
    font-size: 11px;
}}
QPushButton#manageButton:hover {{
    background-color: #2A241A;
}}
QPushButton#starButton {{
    color: {MUTED};
    background: transparent;
    border: 1px solid transparent;
    min-height: 30px;
    padding: 0 8px;
    font-size: 12px;
}}
QPushButton#starButton:hover {{
    color: {ACCENT};
    background-color: #211F1A;
}}
QPushButton#starButton:checked {{
    color: {ACCENT};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    width: 8px;
    margin: 4px 0;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: #2A3948;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3A4D5E;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: none;
}}
QProgressBar {{
    border: none;
    border-radius: 4px;
    background-color: #1A2633;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background-color: {ACCENT};
}}
QDialog {{
    background-color: {BG};
}}
QToolTip {{
    color: {TEXT};
    background-color: {SURFACE_RAISED};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}
QMessageBox {{
    background-color: {SURFACE};
}}
"""


def apply_theme(app) -> None:
    """Apply typography and the global stylesheet to a QApplication."""

    app.setStyleSheet(APP_STYLE)
