"""Modal list for reviewing and restoring temporarily excluded restaurants."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from foodluck.models import Location
from foodluck.storage.database import Database
from foodluck.ui.widgets import Badge, Card, EmptyState, GlyphAvatar


class ExcludedDialog(QDialog):
    changed = Signal()

    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self.database = database
        self.setWindowTitle("已排除的餐厅")
        self.setModal(True)
        self.resize(620, 540)
        self.setMinimumSize(520, 420)
        self._build()
        self.reload()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(14)

        title = QLabel("已排除的餐厅")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 24px;")
        subtitle = QLabel("排除只会让餐厅暂时退出抽签，不会删除收藏或历史。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.list_layout = QVBoxLayout(self.inner)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        footer = QHBoxLayout()
        self.count_badge = Badge("0 家", "quiet")
        self.restore_all_button = QPushButton("恢复全部")
        self.restore_all_button.setObjectName("secondary")
        self.restore_all_button.setCursor(Qt.PointingHandCursor)
        self.restore_all_button.clicked.connect(self._restore_all)
        close_button = QPushButton("完成")
        close_button.setObjectName("primary")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.accept)
        footer.addWidget(self.count_badge)
        footer.addStretch(1)
        footer.addWidget(self.restore_all_button)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def reload(self) -> None:
        self._clear()
        entries = self.database.list_exclusions()
        self.count_badge.setText("{} 家".format(len(entries)))
        self.restore_all_button.setEnabled(bool(entries))
        if not entries:
            self.list_layout.addWidget(
                EmptyState(
                    "没有被排除的餐厅",
                    "在结果卡片上点「暂时排除」，它就会出现在这里。",
                    "↺",
                )
            )
            return

        for entry in entries:
            restaurant = entry.restaurant
            row = Card("excludedRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(14, 11, 14, 11)
            layout.setSpacing(12)
            layout.addWidget(GlyphAvatar(restaurant.cuisine, 42))

            text = QVBoxLayout()
            text.setSpacing(2)
            name = QLabel(restaurant.name)
            name.setObjectName("rowTitle")
            meta = QLabel(
                "{} · {} · {} · {}".format(
                    restaurant.cuisine,
                    restaurant.distance_label,
                    restaurant.price_label,
                    "模拟" if restaurant.is_mock else "OSM",
                )
            )
            meta.setObjectName("muted")
            text.addWidget(name)
            text.addWidget(meta)
            layout.addLayout(text, 1)

            restore = QPushButton("恢复")
            restore.setObjectName("manageButton")
            restore.setCursor(Qt.PointingHandCursor)
            restore.clicked.connect(
                lambda _checked=False, restaurant_id=restaurant.id: self._restore_one(
                    restaurant_id
                )
            )
            layout.addWidget(restore, 0, Qt.AlignVCenter)
            self.list_layout.addWidget(row)

        self.list_layout.addStretch(1)

    def _restore_one(self, restaurant_id: str) -> None:
        self.database.remove_exclusion(restaurant_id)
        self.reload()
        self.changed.emit()

    def _restore_all(self) -> None:
        self.database.clear_exclusions()
        self.reload()
        self.changed.emit()

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()


class CoordinateDialog(QDialog):
    """Enter an arbitrary WGS84 search origin when a preset is not enough."""

    def __init__(self, latitude: float = 22.3045, longitude: float = 114.1795, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义搜索坐标")
        self.setModal(True)
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        title = QLabel("自定义搜索坐标")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 24px;")
        subtitle = QLabel("输入 WGS84 坐标。真实模式会把坐标发送给 OpenStreetMap，用于查询附近餐厅。")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        latitude_row = QHBoxLayout()
        latitude_label = QLabel("纬度")
        latitude_label.setObjectName("fieldLabel")
        self.latitude_spin = QDoubleSpinBox()
        self.latitude_spin.setRange(-90.0, 90.0)
        self.latitude_spin.setDecimals(6)
        self.latitude_spin.setSingleStep(0.001)
        self.latitude_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.latitude_spin.setValue(latitude)
        latitude_row.addWidget(latitude_label, 0)
        latitude_row.addWidget(self.latitude_spin, 1)
        layout.addLayout(latitude_row)

        longitude_row = QHBoxLayout()
        longitude_label = QLabel("经度")
        longitude_label.setObjectName("fieldLabel")
        self.longitude_spin = QDoubleSpinBox()
        self.longitude_spin.setRange(-180.0, 180.0)
        self.longitude_spin.setDecimals(6)
        self.longitude_spin.setSingleStep(0.001)
        self.longitude_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.longitude_spin.setValue(longitude)
        longitude_row.addWidget(longitude_label, 0)
        longitude_row.addWidget(self.longitude_spin, 1)
        layout.addLayout(longitude_row)

        note = QLabel("示例：理大 22.304500, 114.179500。坐标只用于本次搜索。")
        note.setObjectName("helper")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        cancel = QPushButton("取消")
        cancel.setObjectName("secondary")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("使用此坐标")
        confirm.setObjectName("primary")
        confirm.setCursor(Qt.PointingHandCursor)
        confirm.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

    def location(self) -> Location:
        return Location(
            name="自定义坐标",
            latitude=self.latitude_spin.value(),
            longitude=self.longitude_spin.value(),
        )
