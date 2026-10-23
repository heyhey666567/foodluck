"""Reusable visual pieces for the FoodLuck interface."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from foodluck.ui.theme import ACCENT, ACCENT_INK

CUISINE_GLYPHS = {
    "港式": "茶",
    "中餐": "中",
    "川菜": "辣",
    "日料": "鲜",
    "韩餐": "饭",
    "西式": "面",
    "素食": "蔬",
    "东南亚": "香",
    "印度菜": "印",
    "咖啡轻食": "咖",
    "其他": "食",
}


def cuisine_glyph(cuisine: Optional[str]) -> str:
    return CUISINE_GLYPHS.get(cuisine or "", "食")


class Card(QFrame):
    def __init__(self, object_name: str = "card", parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)


class Badge(QLabel):
    def __init__(self, text: str = "", tone: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("badge")
        self.setProperty("tone", tone)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)


class NavButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("nav")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)


class PageHeader(QWidget):
    """Consistent page title block with an optional right-side badge."""

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        text_column = QVBoxLayout()
        text_column.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        text_column.addWidget(self.title_label)
        text_column.addWidget(self.subtitle_label)

        self.right_layout = QHBoxLayout()
        self.right_layout.setSpacing(8)
        self.right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addLayout(text_column, 1)
        layout.addLayout(self.right_layout)


class GlyphAvatar(QLabel):
    def __init__(self, cuisine: Optional[str], size: int = 46, parent=None):
        super().__init__(cuisine_glyph(cuisine), parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "background-color: #292318; color: {}; border: 1px solid #4A3A1D; "
            "border-radius: 13px; font-size: {}px; font-weight: 800;".format(
                ACCENT, max(16, size // 2 - 3)
            )
        )


class EmptyState(QWidget):
    def __init__(self, title: str, body: str, glyph: str = "◇", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 34, 20, 34)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel(glyph)
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(62, 62)

        title_label = QLabel(title)
        title_label.setObjectName("emptyTitle")
        title_label.setAlignment(Qt.AlignCenter)
        body_label = QLabel(body)
        body_label.setObjectName("muted")
        body_label.setAlignment(Qt.AlignCenter)
        body_label.setWordWrap(True)
        body_label.setMaximumWidth(420)

        layout.addStretch(1)
        layout.addWidget(icon, 0, Qt.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addStretch(1)


class FoodOrb(QWidget):
    """Painted food mark with a subtle spinning ring while drawing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(154, 154)
        self._glyph = "运"
        self._angle = 0.0
        self._rolling = False
        self._spin = QPropertyAnimation(self, b"angle", self)
        self._spin.setStartValue(0.0)
        self._spin.setEndValue(360.0)
        self._spin.setDuration(900)
        self._spin.setLoopCount(-1)
        self._spin.setEasingCurve(QEasingCurve.Linear)

    def _get_angle(self) -> float:
        return self._angle

    def _set_angle(self, value: float) -> None:
        self._angle = float(value)
        self.update()

    angle = Property(float, _get_angle, _set_angle)

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph[:1] if glyph else "食"
        self.update()

    def set_rolling(self, rolling: bool) -> None:
        if self._rolling == rolling:
            return
        self._rolling = rolling
        if rolling:
            self._spin.start()
        else:
            self._spin.stop()
            self._angle = 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        radius = 58.0

        # Layered translucency gives a soft glow without external assets.
        painter.setPen(Qt.NoPen)
        for spread, alpha in ((16, 16), (10, 28), (4, 36)):
            painter.setBrush(QColor(255, 157, 68, alpha))
            painter.drawEllipse(center, radius + spread, radius + spread)

        gradient = QRadialGradient(
            center.x() - 20,
            center.y() - 26,
            radius * 1.7,
        )
        gradient.setColorAt(0.0, QColor("#FFD08A"))
        gradient.setColorAt(0.42, QColor(ACCENT))
        gradient.setColorAt(1.0, QColor("#E86E36"))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(255, 214, 155, 130), 1.2))
        painter.drawEllipse(center, radius, radius)

        highlight = QLinearGradient(0, center.y() - radius, 0, center.y() + radius)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 80))
        highlight.setColorAt(0.55, QColor(255, 255, 255, 0))
        painter.setBrush(highlight)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius - 2, radius - 2)

        if self._rolling:
            painter.save()
            painter.translate(center)
            painter.rotate(self._angle)
            pen = QPen(QColor(255, 225, 178, 220), 3.2)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(QRectF(-71, -71, 142, 142), 20 * 16, 92 * 16)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#FFF0D2"))
            painter.drawEllipse(QRectF(61, -11.5, 23, 23))
            painter.restore()

        font = QFont("PingFang SC", 47)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(ACCENT_INK))
        painter.drawText(self.rect(), Qt.AlignCenter, self._glyph)
        painter.end()


class Toast(QLabel):
    """A lightweight non-blocking message that fades away."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setWordWrap(False)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(170)
        self._animation.finished.connect(self._on_animation_finished)
        self._fading_out = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, duration_ms: int = 2200) -> None:
        self.setText(text)
        self.adjustSize()
        self._fading_out = False
        self._effect.setOpacity(0.0)
        self.show()
        self.raise_()
        self._animation.stop()
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()
        self._timer.start(duration_ms)

    def _fade_out(self) -> None:
        self._fading_out = True
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.InCubic)
        self._animation.start()

    def _on_animation_finished(self) -> None:
        if self._fading_out:
            self.hide()


def muted_divider() -> QFrame:
    divider = QFrame()
    divider.setFixedHeight(1)
    divider.setStyleSheet("background-color: #1E2A37; border: none;")
    return divider
