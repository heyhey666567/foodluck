"""The three main pages: draw, favorites, and history."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from foodluck.data.locations import LOCATION_PRESETS, find_location
from foodluck.models import (
    CUISINES,
    DEFAULT_LOCATION,
    RADIUS_OPTIONS,
    BudgetTier,
    DataSource,
    DrawMode,
    HistoryEntry,
    Location,
    Restaurant,
    RestaurantQuery,
    SavedRestaurant,
)
from foodluck.ui.dialogs import CoordinateDialog
from foodluck.ui.widgets import (
    Badge,
    Card,
    EmptyState,
    FoodOrb,
    GlyphAvatar,
    PageHeader,
    cuisine_glyph,
)


def _field_block(label_text: str, widget: QWidget, stretch: int = 1) -> QWidget:
    block = QWidget()
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    label = QLabel(label_text)
    label.setObjectName("fieldLabel")
    layout.addWidget(label)
    layout.addWidget(widget)
    block.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return block


def _set_combo_by_data(combo: QComboBox, value) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


class DrawPage(QWidget):
    """Filter controls, the draw ritual, and the live candidate summary."""

    draw_requested = Signal()
    reroll_requested = Signal()
    confirm_requested = Signal()
    favorite_requested = Signal()
    exclude_requested = Signal()
    filters_changed = Signal()
    mode_changed = Signal(object)
    source_changed = Signal(object)
    manage_exclusions_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self._mode = DrawMode.NORMAL
        self._source = DataSource.DEMO
        self._current: Optional[Restaurant] = None
        self._rolling = False
        self._searching = False
        self._confirmed = False
        self._preview_names: List[str] = []
        self._preview_index = 0
        self._excluded_total = 0
        self._custom_location: Optional[Location] = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(78)
        self._preview_timer.timeout.connect(self._tick_preview)
        self._build()
        self._connect()
        self.render_idle()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        header = PageHeader(
            "今天吃什么？",
            "筛选附近餐厅，把纠结交给一次公平的抽签。",
        )
        self.source_badge = Badge("模拟数据 · 非真实餐厅", "accent")
        header.right_layout.addWidget(self.source_badge)
        header.right_layout.addWidget(Badge("V0.2", "quiet"))
        root.addWidget(header)

        root.addWidget(self._build_filter_card())
        root.addLayout(self._build_content(), 1)

    def _build_filter_card(self) -> QWidget:
        card = Card("filterCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("先缩小范围")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addSpacing(8)

        self._source_group = QButtonGroup(self)
        self._source_group.setExclusive(True)
        self.demo_source_button = QPushButton("演示数据")
        self.live_source_button = QPushButton("真实附近")
        for button in (self.demo_source_button, self.live_source_button):
            button.setObjectName("sourceButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            self._source_group.addButton(button)
            title_row.addWidget(button)
        self.demo_source_button.setChecked(True)

        self.source_hint = QLabel("筛选即时生效")
        self.source_hint.setObjectName("helper")
        title_row.addStretch(1)
        title_row.addWidget(self.source_hint)
        layout.addLayout(title_row)

        fields = QHBoxLayout()
        fields.setSpacing(12)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：香港理工大学附近")
        self.location_edit.setMinimumWidth(210)

        self.live_location_combo = QComboBox()
        for location in LOCATION_PRESETS:
            self.live_location_combo.addItem(location.name, location)
        self.live_location_combo.setMinimumWidth(170)
        self.coordinate_button = QPushButton("坐标")
        self.coordinate_button.setObjectName("coordinateButton")
        self.coordinate_button.setCursor(Qt.PointingHandCursor)
        self.coordinate_button.setToolTip("输入任意 WGS84 经纬度")
        live_location_row = QWidget()
        live_location_layout = QHBoxLayout(live_location_row)
        live_location_layout.setContentsMargins(0, 0, 0, 0)
        live_location_layout.setSpacing(6)
        live_location_layout.addWidget(self.live_location_combo, 1)
        live_location_layout.addWidget(self.coordinate_button)

        self.location_stack = QStackedWidget()
        self.location_stack.addWidget(self.location_edit)
        self.location_stack.addWidget(live_location_row)
        self.location_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.radius_combo = QComboBox()
        for radius in RADIUS_OPTIONS:
            label = "{} 米".format(int(radius * 1000)) if radius < 1 else "{:g} 公里".format(radius)
            self.radius_combo.addItem(label, radius)
        self.radius_combo.setCurrentIndex(2)
        self.radius_combo.setMinimumWidth(108)

        self.cuisine_combo = QComboBox()
        self.cuisine_combo.addItem("菜系不限", None)
        for cuisine in CUISINES:
            self.cuisine_combo.addItem(cuisine, cuisine)
        self.cuisine_combo.setMinimumWidth(116)

        self.budget_combo = QComboBox()
        for tier in (
            BudgetTier.ANY,
            BudgetTier.UNDER_50,
            BudgetTier.FROM_50_TO_100,
            BudgetTier.OVER_100,
        ):
            self.budget_combo.addItem(tier.label, tier.value)
        self.budget_combo.setMinimumWidth(134)

        self.open_check = QCheckBox("只看营业中")
        self.open_check.setMinimumHeight(38)

        fields.addWidget(_field_block("在哪里吃", self.location_stack), 3)
        fields.addWidget(_field_block("搜索范围", self.radius_combo), 1)
        fields.addWidget(_field_block("菜系", self.cuisine_combo), 1)
        fields.addWidget(_field_block("预算", self.budget_combo), 1)
        fields.addWidget(_field_block("营业状态", self.open_check), 0)
        layout.addLayout(fields)

        self.filter_helper = QLabel(
            "位置仅作记录；演示模式使用以理大周边为背景的虚构餐厅，不会联网搜索。"
        )
        self.filter_helper.setObjectName("helper")
        self.filter_helper.setWordWrap(True)
        layout.addWidget(self.filter_helper)
        return card

    def _build_content(self) -> QHBoxLayout:
        content = QHBoxLayout()
        content.setSpacing(16)
        content.addWidget(self._build_hero(), 1)
        content.addLayout(self._build_side(), 0)
        return content

    def _build_hero(self) -> QWidget:
        hero = Card("heroCard")
        hero.setMinimumHeight(448)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(26, 20, 26, 20)
        layout.setSpacing(6)

        top = QHBoxLayout()
        eyebrow = QLabel("本次抽签")
        eyebrow.setObjectName("sectionTitle")
        top.addWidget(eyebrow)
        top.addStretch(1)
        self.hero_badge = Badge("模拟 · 未验证", "accent")
        top.addWidget(self.hero_badge)
        self.favorite_button = QPushButton("☆ 收藏")
        self.favorite_button.setObjectName("starButton")
        self.favorite_button.setCheckable(True)
        self.favorite_button.setCursor(Qt.PointingHandCursor)
        self.favorite_button.hide()
        top.addWidget(self.favorite_button)
        layout.addLayout(top)

        center = QVBoxLayout()
        center.setSpacing(4)
        center.addStretch(1)

        self.orb = FoodOrb()
        center.addWidget(self.orb, 0, Qt.AlignHCenter)
        center.addSpacing(3)

        self.state_label = QLabel("运气即将上菜")
        self.state_label.setObjectName("heroEyebrow")
        self.state_label.setAlignment(Qt.AlignCenter)
        center.addWidget(self.state_label)

        self.name_label = QLabel("今天，把选择交给运气")
        self.name_label.setObjectName("heroName")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        center.addWidget(self.name_label)

        self.meta_widget = QWidget()
        meta_row = QHBoxLayout(self.meta_widget)
        meta_row.setContentsMargins(0, 3, 0, 2)
        meta_row.setSpacing(6)
        meta_row.addStretch(1)
        self.cuisine_badge = Badge("", "quiet")
        self.distance_badge = Badge("", "quiet")
        self.price_badge = Badge("", "quiet")
        self.open_badge = Badge("", "quiet")
        for badge in (
            self.cuisine_badge,
            self.distance_badge,
            self.price_badge,
            self.open_badge,
        ):
            meta_row.addWidget(badge)
        meta_row.addStretch(1)
        self.meta_widget.hide()
        center.addWidget(self.meta_widget)

        self.address_label = QLabel("点击「开始抽签」，从候选池中公平抽出一家。")
        self.address_label.setObjectName("heroAddress")
        self.address_label.setAlignment(Qt.AlignCenter)
        self.address_label.setWordWrap(True)
        center.addWidget(self.address_label)

        self.source_note = QLabel("所有餐厅均为虚构测试数据，不构成真实推荐。")
        self.source_note.setObjectName("helper")
        self.source_note.setAlignment(Qt.AlignCenter)
        self.source_note.setWordWrap(True)
        center.addWidget(self.source_note)
        center.addStretch(1)
        layout.addLayout(center, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.draw_button = QPushButton("开始抽签")
        self.draw_button.setObjectName("primary")
        self.draw_button.setCursor(Qt.PointingHandCursor)
        self.draw_button.setMinimumWidth(150)
        self.confirm_button = QPushButton("就是这家")
        self.confirm_button.setObjectName("primary")
        self.confirm_button.setCursor(Qt.PointingHandCursor)
        self.confirm_button.setMinimumWidth(132)
        self.reroll_button = QPushButton("重新抽签")
        self.reroll_button.setObjectName("secondary")
        self.reroll_button.setCursor(Qt.PointingHandCursor)
        self.exclude_button = QPushButton("暂时排除")
        self.exclude_button.setObjectName("ghost")
        self.exclude_button.setCursor(Qt.PointingHandCursor)
        actions.addWidget(self.draw_button)
        actions.addWidget(self.confirm_button)
        actions.addWidget(self.reroll_button)
        actions.addStretch(1)
        actions.addWidget(self.exclude_button)
        layout.addLayout(actions)
        return hero

    def _build_side(self) -> QVBoxLayout:
        side = QVBoxLayout()
        side.setSpacing(12)
        side.setContentsMargins(0, 0, 0, 0)

        candidate = Card("sideCard")
        candidate_layout = QVBoxLayout(candidate)
        candidate_layout.setContentsMargins(18, 15, 18, 15)
        candidate_layout.setSpacing(5)
        title_row = QHBoxLayout()
        title = QLabel("候选池")
        title.setObjectName("sectionTitle")
        self.pool_badge = Badge("实时", "mint")
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.pool_badge)
        candidate_layout.addLayout(title_row)

        count_row = QHBoxLayout()
        count_row.setSpacing(6)
        self.count_label = QLabel("—")
        self.count_label.setObjectName("bigNumber")
        self.count_unit = QLabel("家可选")
        self.count_unit.setObjectName("muted")
        count_row.addWidget(self.count_label)
        count_row.addWidget(self.count_unit, 0, Qt.AlignBottom)
        count_row.addStretch(1)
        candidate_layout.addLayout(count_row)

        self.pool_detail = QLabel("正在读取候选…")
        self.pool_detail.setObjectName("muted")
        self.pool_detail.setWordWrap(True)
        self.open_detail = QLabel("")
        self.open_detail.setObjectName("muted")
        self.cuisine_summary = QLabel("")
        self.cuisine_summary.setObjectName("helper")
        self.cuisine_summary.setWordWrap(True)
        candidate_layout.addWidget(self.pool_detail)
        candidate_layout.addWidget(self.open_detail)
        candidate_layout.addWidget(self.cuisine_summary)
        side.addWidget(candidate)

        mode_card = Card("modeCard")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(18, 15, 18, 15)
        mode_layout.setSpacing(8)
        mode_title = QLabel("玩法")
        mode_title.setObjectName("sectionTitle")
        mode_layout.addWidget(mode_title)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self.normal_button = QPushButton("普通模式")
        self.fate_button = QPushButton("命运模式")
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for button in (self.normal_button, self.fate_button):
            button.setObjectName("modeButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            self._mode_group.addButton(button)
            mode_row.addWidget(button)
        self.normal_button.setChecked(True)
        mode_layout.addLayout(mode_row)
        self.mode_description = QLabel(DrawMode.NORMAL.description)
        self.mode_description.setObjectName("helper")
        self.mode_description.setWordWrap(True)
        mode_layout.addWidget(self.mode_description)
        side.addWidget(mode_card)

        exclude_card = Card("excludeCard")
        exclude_layout = QVBoxLayout(exclude_card)
        exclude_layout.setContentsMargins(18, 14, 18, 14)
        exclude_layout.setSpacing(7)
        exclude_title_row = QHBoxLayout()
        exclude_title = QLabel("已排除")
        exclude_title.setObjectName("sectionTitle")
        self.excluded_count_label = QLabel("0 家")
        self.excluded_count_label.setObjectName("smallNumber")
        exclude_title_row.addWidget(exclude_title)
        exclude_title_row.addStretch(1)
        exclude_title_row.addWidget(self.excluded_count_label)
        exclude_layout.addLayout(exclude_title_row)
        exclude_hint = QLabel("暂时不想吃的店会留在这里，随时可以恢复。")
        exclude_hint.setObjectName("helper")
        exclude_hint.setWordWrap(True)
        exclude_layout.addWidget(exclude_hint)
        self.manage_button = QPushButton("查看并恢复")
        self.manage_button.setObjectName("manageButton")
        self.manage_button.setCursor(Qt.PointingHandCursor)
        exclude_layout.addWidget(self.manage_button)
        side.addWidget(exclude_card)
        side.addStretch(1)
        return side

    def _connect(self) -> None:
        self.location_edit.textChanged.connect(self._emit_filters)
        self.live_location_combo.currentIndexChanged.connect(self._emit_filters)
        self.coordinate_button.clicked.connect(self._open_coordinate_dialog)
        self.demo_source_button.clicked.connect(
            lambda: self._select_source(DataSource.DEMO)
        )
        self.live_source_button.clicked.connect(
            lambda: self._select_source(DataSource.LIVE)
        )
        self.radius_combo.currentIndexChanged.connect(self._emit_filters)
        self.cuisine_combo.currentIndexChanged.connect(self._emit_filters)
        self.budget_combo.currentIndexChanged.connect(self._emit_filters)
        self.open_check.toggled.connect(self._emit_filters)
        self.draw_button.clicked.connect(self.draw_requested)
        self.confirm_button.clicked.connect(self.confirm_requested)
        self.reroll_button.clicked.connect(self.reroll_requested)
        self.favorite_button.clicked.connect(self.favorite_requested)
        self.exclude_button.clicked.connect(self.exclude_requested)
        self.manage_button.clicked.connect(self.manage_exclusions_requested)
        self.normal_button.clicked.connect(lambda: self._select_mode(DrawMode.NORMAL))
        self.fate_button.clicked.connect(lambda: self._select_mode(DrawMode.FATE))

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------
    @property
    def mode(self) -> DrawMode:
        return self._mode

    @property
    def source(self) -> DataSource:
        return self._source

    @property
    def current(self) -> Optional[Restaurant]:
        return self._current

    @property
    def rolling(self) -> bool:
        return self._rolling

    @property
    def searching(self) -> bool:
        return self._searching

    @property
    def confirmed(self) -> bool:
        return self._confirmed

    @property
    def live_location(self) -> Optional[Location]:
        data = self.live_location_combo.currentData()
        return data if isinstance(data, Location) else None

    def query(self) -> RestaurantQuery:
        if self._source is DataSource.LIVE:
            location = self.live_location
            return RestaurantQuery(
                location=location.name if location else "未选择地点",
                radius_km=float(self.radius_combo.currentData() or 1.0),
                cuisine=self.cuisine_combo.currentData(),
                budget=BudgetTier.ANY,
                open_only=False,
                latitude=location.latitude if location else None,
                longitude=location.longitude if location else None,
            )
        location = self.location_edit.text().strip() or DEFAULT_LOCATION
        return RestaurantQuery(
            location=location,
            radius_km=float(self.radius_combo.currentData() or 1.0),
            cuisine=self.cuisine_combo.currentData(),
            budget=BudgetTier.from_value(self.budget_combo.currentData()),
            open_only=self.open_check.isChecked(),
        )

    def settings_snapshot(self) -> Dict[str, str]:
        live_location = self.live_location
        return {
            "location": self.location_edit.text().strip() or DEFAULT_LOCATION,
            "radius_km": "{:g}".format(float(self.radius_combo.currentData() or 1.0)),
            "cuisine": self.cuisine_combo.currentData() or "",
            "budget": BudgetTier.from_value(self.budget_combo.currentData()).value,
            "open_only": "1" if self.open_check.isChecked() else "0",
            "mode": self._mode.value,
            "data_source": self._source.value,
            "live_location_name": live_location.name if live_location else "香港理工大学",
            "live_latitude": "{:.6f}".format(live_location.latitude) if live_location else "22.304500",
            "live_longitude": "{:.6f}".format(live_location.longitude) if live_location else "114.179500",
        }

    def apply_settings(self, values: Dict[str, str]) -> None:
        blocker = QSignalBlocker(self)
        self.location_edit.setText(values.get("location") or DEFAULT_LOCATION)
        try:
            radius = float(values.get("radius_km", "1.0"))
        except ValueError:
            radius = 1.0
        _set_combo_by_data(self.radius_combo, radius)
        cuisine = values.get("cuisine") or None
        _set_combo_by_data(self.cuisine_combo, cuisine)
        _set_combo_by_data(
            self.budget_combo,
            BudgetTier.from_value(values.get("budget")).value,
        )
        self.open_check.setChecked(values.get("open_only") == "1")
        self.set_mode(DrawMode.from_value(values.get("mode")))
        self._restore_live_location(values)
        self.set_source(DataSource.from_value(values.get("data_source")))
        del blocker

    def _restore_live_location(self, values: Dict[str, str]) -> None:
        try:
            latitude = float(values.get("live_latitude", "22.304500"))
            longitude = float(values.get("live_longitude", "114.179500"))
        except ValueError:
            latitude, longitude = 22.3045, 114.1795
        name = values.get("live_location_name") or "香港理工大学"
        preset = find_location(name)
        if (
            preset
            and abs(preset.latitude - latitude) < 1e-6
            and abs(preset.longitude - longitude) < 1e-6
        ):
            for index in range(self.live_location_combo.count()):
                data = self.live_location_combo.itemData(index)
                if isinstance(data, Location) and data.name == preset.name:
                    self.live_location_combo.setCurrentIndex(index)
                    return
        custom = Location(name or "自定义坐标", latitude, longitude)
        self._set_custom_location(custom, select=True)

    def set_source(self, source: DataSource) -> None:
        self._source = source
        self.demo_source_button.setChecked(source is DataSource.DEMO)
        self.live_source_button.setChecked(source is DataSource.LIVE)
        self.location_stack.setCurrentIndex(0 if source is DataSource.DEMO else 1)
        if source is DataSource.LIVE:
            self.source_badge.setText("OpenStreetMap · 未验证")
            self.source_badge.set_tone("mint")
            self.hero_badge.setText("OSM · 未验证")
            self.hero_badge.set_tone("mint")
            self.source_hint.setText("联网搜索 · 最长 12 秒")
            self.filter_helper.setText(
                "真实结果来自 OpenStreetMap（ODbL），优先 Overpass、繁忙时回退 Nominatim；"
                "可能不完整，且不提供可靠的人均价格/营业状态，因此这两项筛选已停用。"
            )
            self.budget_combo.setToolTip("OpenStreetMap 不提供可靠的人均价格")
            self.open_check.setToolTip("OpenStreetMap 不提供可靠的营业状态")
        else:
            self.source_badge.setText("模拟数据 · 非真实餐厅")
            self.source_badge.set_tone("accent")
            self.hero_badge.setText("模拟 · 未验证")
            self.hero_badge.set_tone("accent")
            self.source_hint.setText("筛选即时生效")
            self.filter_helper.setText(
                "位置仅作记录；演示模式使用以理大周边为背景的虚构餐厅，不会联网搜索。"
            )
            self.budget_combo.setToolTip("")
            self.open_check.setToolTip("")
        self._set_filters_enabled(not self._rolling and not self._searching)
        if self._current is not None:
            self.source_note.setText(self._source_note_for(self._current))

    def _select_source(self, source: DataSource) -> None:
        if self._rolling or self._searching or source is self._source:
            return
        self.set_source(source)
        self.source_changed.emit(source)

    def _open_coordinate_dialog(self) -> None:
        current = self.live_location
        dialog = CoordinateDialog(
            latitude=current.latitude if current else 22.3045,
            longitude=current.longitude if current else 114.1795,
            parent=self,
        )
        if dialog.exec():
            self._set_custom_location(dialog.location(), select=True)
            self.filters_changed.emit()

    def _set_custom_location(self, location: Location, select: bool = True) -> None:
        self._custom_location = location
        label = "自定义 · {:.4f}, {:.4f}".format(location.latitude, location.longitude)
        blocker = QSignalBlocker(self.live_location_combo)
        for index in range(self.live_location_combo.count()):
            data = self.live_location_combo.itemData(index)
            if isinstance(data, Location) and data.name == "自定义坐标":
                self.live_location_combo.setItemText(index, label)
                self.live_location_combo.setItemData(index, location)
                if select:
                    self.live_location_combo.setCurrentIndex(index)
                del blocker
                return
        self.live_location_combo.addItem(label, location)
        if select:
            self.live_location_combo.setCurrentIndex(self.live_location_combo.count() - 1)
        del blocker

    def set_mode(self, mode: DrawMode) -> None:
        self._mode = mode
        self.normal_button.setChecked(mode is DrawMode.NORMAL)
        self.fate_button.setChecked(mode is DrawMode.FATE)
        self.mode_description.setText(mode.description)
        if self._current is not None:
            self.reroll_button.setVisible(mode is DrawMode.NORMAL and not self._rolling)

    def _select_mode(self, mode: DrawMode) -> None:
        if self._rolling or self._searching or mode is self._mode:
            return
        self.set_mode(mode)
        self.mode_changed.emit(mode)

    # ------------------------------------------------------------------
    # Filters and pool summary
    # ------------------------------------------------------------------
    def _emit_filters(self, *args) -> None:
        if self._rolling or self._searching:
            return
        self.filters_changed.emit()

    def set_pool_counts(
        self,
        total: int,
        available: int,
        excluded: int,
        open_count: int,
        cuisine_counts: Dict[str, int],
        open_known: bool = True,
    ) -> None:
        self.count_label.setText(str(available))
        self.count_unit.setText("家可选")
        detail = "本筛选共 {} 家".format(total)
        if excluded:
            detail += " · {} 家已排除".format(excluded)
        self.pool_detail.setText(detail)
        if open_known:
            self.open_detail.setText("其中 {} 家正在营业".format(open_count))
        else:
            self.open_detail.setText("OSM 未提供营业状态与人均价格")
        ranked = sorted(cuisine_counts.items(), key=lambda pair: (-pair[1], pair[0]))
        visible = ranked[:3]
        summary = " · ".join("{} {}".format(name, count) for name, count in visible)
        if len(ranked) > len(visible):
            summary += " · 另有 {} 种".format(len(ranked) - len(visible))
        self.cuisine_summary.setText(summary)
        if available == 0:
            self.pool_badge.setText("暂无")
            self.pool_badge.set_tone("danger")
        else:
            self.pool_badge.setText("实时")
            self.pool_badge.set_tone("mint")

    def set_pool_unsearched(self, location_name: str) -> None:
        self.count_label.setText("?")
        self.count_unit.setText("家待发现")
        self.pool_badge.setText("待搜索")
        self.pool_badge.set_tone("quiet")
        self.pool_detail.setText("尚未搜索 · {}".format(location_name))
        self.open_detail.setText("真实结果来自 OpenStreetMap，可能不完整")
        self.cuisine_summary.setText("点击「搜索并抽签」联网查询附近餐厅")
        if self._current is None and not self._rolling and not self._searching:
            self.draw_button.setText("搜索并抽签")

    def set_excluded_count(self, total: int) -> None:
        self._excluded_total = total
        self.excluded_count_label.setText("{} 家".format(total))
        self.manage_button.setEnabled(total > 0 and not self._rolling)
        if total == 0:
            self.manage_button.setText("暂无排除")
        else:
            self.manage_button.setText("查看并恢复")

    # ------------------------------------------------------------------
    # Result states
    # ------------------------------------------------------------------
    def render_idle(self) -> None:
        self._stop_rolling()
        self._searching = False
        self._current = None
        self._confirmed = False
        self.meta_widget.hide()
        self.favorite_button.hide()
        self.favorite_button.setChecked(False)
        self.confirm_button.hide()
        self.reroll_button.hide()
        self.exclude_button.hide()
        self.draw_button.setEnabled(True)
        self.draw_button.show()
        if self._source is DataSource.LIVE:
            self.orb.set_glyph("寻")
            self.state_label.setText("真实餐厅，实时搜索")
            self.name_label.setText("去附近，找一家真的")
            self.address_label.setText(
                "选择地点，点击「搜索并抽签」，联网查找附近餐厅。"
            )
            self.source_note.setText(
                "结果来自 OpenStreetMap（ODbL），可能不完整；不会生成虚假餐厅。"
            )
            self.draw_button.setText("搜索并抽签")
        else:
            self.orb.set_glyph("运")
            self.state_label.setText("运气即将上菜")
            self.name_label.setText("今天，把选择交给运气")
            self.address_label.setText("点击「开始抽签」，从候选池中公平抽出一家。")
            self.source_note.setText("所有餐厅均为虚构测试数据，不构成真实推荐。")
            self.draw_button.setText("开始抽签")
        self._set_filters_enabled(True)

    def begin_search(self, location_name: str, radius_km: float) -> None:
        self._stop_rolling()
        self._searching = True
        self._current = None
        self._confirmed = False
        self.orb.set_glyph("寻")
        self.orb.set_rolling(True)
        self.state_label.setText("正在寻找真实餐厅")
        self.name_label.setText("查询 OpenStreetMap…")
        self.meta_widget.hide()
        self.address_label.setText(
            "正在搜索「{}」周边 {:g} 公里内的餐厅。".format(location_name, radius_km)
        )
        self.source_note.setText("联网请求最长等待 12 秒，界面不会卡住。")
        self.favorite_button.hide()
        self.confirm_button.hide()
        self.reroll_button.hide()
        self.exclude_button.hide()
        self.draw_button.setText("搜索中…")
        self.draw_button.setEnabled(False)
        self.draw_button.show()
        self._set_filters_enabled(False)

    def end_search(self) -> None:
        self._searching = False
        self.orb.set_rolling(False)
        self._set_filters_enabled(True)

    def begin_roll(self, preview_names: Sequence[str]) -> None:
        self._searching = False
        self._rolling = True
        self._current = None
        self._confirmed = False
        self._preview_names = list(preview_names)
        self._preview_index = 0
        self.orb.set_glyph("?")
        self.orb.set_rolling(True)
        self.state_label.setText("命运正在挑选")
        self.name_label.setText("正在洗牌…")
        self.meta_widget.hide()
        self.address_label.setText(
            "正在从 {} 家候选中等概率抽取。".format(len(self._preview_names))
        )
        self.source_note.setText("这一次，让随机数替你做决定。")
        self.favorite_button.hide()
        self.confirm_button.hide()
        self.reroll_button.hide()
        self.exclude_button.hide()
        self.draw_button.setText("抽签中…")
        self.draw_button.setEnabled(False)
        self.draw_button.show()
        self._set_filters_enabled(False)
        self._preview_timer.start()

    def _tick_preview(self) -> None:
        if not self._preview_names:
            return
        self._preview_index = (self._preview_index + 1) % len(self._preview_names)
        self.name_label.setText(self._preview_names[self._preview_index])

    def _stop_rolling(self) -> None:
        self._rolling = False
        self._preview_timer.stop()
        self.orb.set_rolling(False)

    def render_result(
        self,
        restaurant: Restaurant,
        favorite: bool,
        confirmed: bool,
        mode: DrawMode,
    ) -> None:
        self._stop_rolling()
        self._current = restaurant
        self._confirmed = confirmed
        self._set_filters_enabled(True)
        self.set_mode(mode)
        self.orb.set_glyph(cuisine_glyph(restaurant.cuisine))
        self.state_label.setText(
            "已记入你的餐单"
            if confirmed
            else ("命运已替你决定" if mode is DrawMode.FATE else "今天就吃这家")
        )
        self.name_label.setText(restaurant.name)
        self.cuisine_badge.setText(restaurant.cuisine or "菜系暂无数据")
        self.distance_badge.setText(restaurant.distance_label)
        self.price_badge.setText(restaurant.price_label)
        self.open_badge.setText(restaurant.open_label)
        self.open_badge.set_tone(
            "mint" if restaurant.is_open is True else ("danger" if restaurant.is_open is False else "quiet")
        )
        self.meta_widget.show()
        self.address_label.setText("地址 · {}".format(restaurant.address_label))
        self.source_note.setText(self._source_note_for(restaurant))
        self.favorite_button.show()
        self.favorite_button.setChecked(favorite)
        self._sync_favorite_label(favorite)
        self.confirm_button.show()
        self.confirm_button.setEnabled(not confirmed)
        self.confirm_button.setText("已记入餐单" if confirmed else "就是这家")
        self.reroll_button.setVisible(mode is DrawMode.NORMAL)
        self.exclude_button.show()
        self.draw_button.hide()

    def mark_confirmed(self) -> None:
        self._confirmed = True
        self.state_label.setText("已记入你的餐单")
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText("已记入餐单")

    def set_favorite(self, favorite: bool) -> None:
        self.favorite_button.setChecked(favorite)
        self._sync_favorite_label(favorite)

    def _sync_favorite_label(self, favorite: bool) -> None:
        self.favorite_button.setText("★ 已收藏" if favorite else "☆ 收藏")

    def show_error(self, message: str) -> None:
        self._stop_rolling()
        self._searching = False
        self._current = None
        self._confirmed = False
        self.orb.set_glyph("空")
        self.state_label.setText("这一签，没有结果")
        self.name_label.setText("暂时没有可选餐厅")
        self.meta_widget.hide()
        self.address_label.setText(message)
        if self._source is DataSource.LIVE:
            self.source_note.setText("检查网络后重试，或缩小搜索范围、换一个菜系。")
            self.draw_button.setText("重新搜索")
        else:
            self.source_note.setText("放宽距离、换一个菜系，或恢复已排除的餐厅后再试。")
            self.draw_button.setText("再试一次")
        self.favorite_button.hide()
        self.confirm_button.hide()
        self.reroll_button.hide()
        self.exclude_button.hide()
        self.draw_button.setEnabled(True)
        self.draw_button.show()
        self._set_filters_enabled(True)

    def _source_note_for(self, restaurant: Restaurant) -> str:
        if restaurant.is_mock:
            return "模拟数据 · 未经验证 · 地址为测试地址，并非真实店铺。"
        service = "Nominatim" if "Nominatim" in restaurant.source_label else "Overpass"
        return (
            "OpenStreetMap · {} · © contributors · ODbL · 信息可能不完整；"
            "营业状态与人均价格暂无数据。".format(service)
        )

    def _set_filters_enabled(self, enabled: bool) -> None:
        for widget in (
            self.location_edit,
            self.live_location_combo,
            self.coordinate_button,
            self.radius_combo,
            self.cuisine_combo,
            self.normal_button,
            self.fate_button,
            self.demo_source_button,
            self.live_source_button,
        ):
            widget.setEnabled(enabled)
        supports_extra_filters = self._source is DataSource.DEMO
        self.budget_combo.setEnabled(enabled and supports_extra_filters)
        self.open_check.setEnabled(enabled and supports_extra_filters)
        self.manage_button.setEnabled(enabled and self._excluded_total > 0)


class FavoritesPage(QWidget):
    remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        header = PageHeader(
            "我的收藏",
            "喜欢的餐厅先放在这里，下一次纠结时更容易找回来。",
        )
        self.count_badge = Badge("0 家", "quiet")
        header.right_layout.addWidget(self.count_badge)
        root.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.list_layout = QVBoxLayout(self.inner)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

    def render(self, entries: List[SavedRestaurant]) -> None:
        self._clear()
        self.count_badge.setText("{} 家".format(len(entries)))
        if not entries:
            self.list_layout.addWidget(
                EmptyState(
                    "还没有收藏",
                    "抽到喜欢的餐厅时，点一下结果卡片上的「☆ 收藏」，它就会出现在这里。",
                    "☆",
                )
            )
            return

        for entry in entries:
            restaurant = entry.restaurant
            row = Card("favoriteRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(16, 13, 16, 13)
            layout.setSpacing(13)
            layout.addWidget(GlyphAvatar(restaurant.cuisine))

            text = QVBoxLayout()
            text.setSpacing(3)
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
            meta.setObjectName("soft")
            address = QLabel(restaurant.address_label)
            address.setObjectName("muted")
            address.setWordWrap(True)
            text.addWidget(name)
            text.addWidget(meta)
            text.addWidget(address)
            layout.addLayout(text, 1)

            remove = QPushButton("移出收藏")
            remove.setObjectName("ghost")
            remove.setCursor(Qt.PointingHandCursor)
            remove.clicked.connect(
                lambda _checked=False, restaurant_id=restaurant.id: self.remove_requested.emit(
                    restaurant_id
                )
            )
            layout.addWidget(remove, 0, Qt.AlignVCenter)
            self.list_layout.addWidget(row)

        self.list_layout.addStretch(1)

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()


class HistoryPage(QWidget):
    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        header = PageHeader(
            "用餐记录",
            "只记录你按下「就是这家」的选择，方便回看最近吃过什么。",
        )
        self.count_badge = Badge("0 次", "quiet")
        self.clear_button = QPushButton("清空记录")
        self.clear_button.setObjectName("dangerGhost")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_requested)
        header.right_layout.addWidget(self.count_badge)
        header.right_layout.addWidget(self.clear_button)
        root.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.list_layout = QVBoxLayout(self.inner)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

    def render(self, entries: List[HistoryEntry]) -> None:
        self._clear()
        self.count_badge.setText("{} 次".format(len(entries)))
        self.clear_button.setVisible(bool(entries))
        if not entries:
            self.list_layout.addWidget(
                EmptyState(
                    "还没有用餐记录",
                    "抽中一家餐厅后点「就是这家」，它就会被记在这里。记录只保存在本机。",
                    "◷",
                )
            )
            return

        for entry in entries:
            restaurant = entry.restaurant
            row = Card("historyRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(16, 13, 16, 13)
            layout.setSpacing(13)
            layout.addWidget(GlyphAvatar(restaurant.cuisine))

            text = QVBoxLayout()
            text.setSpacing(3)
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
            meta.setObjectName("soft")
            address = QLabel(restaurant.address_label)
            address.setObjectName("muted")
            address.setWordWrap(True)
            text.addWidget(name)
            text.addWidget(meta)
            text.addWidget(address)
            layout.addLayout(text, 1)

            right = QVBoxLayout()
            right.setSpacing(5)
            right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            mode = Badge(
                entry.mode.label,
                "accent" if entry.mode is DrawMode.FATE else "quiet",
            )
            right.addWidget(mode, 0, Qt.AlignRight)
            time_label = QLabel(
                entry.confirmed_at.astimezone().strftime("%m月%d日 %H:%M")
            )
            time_label.setObjectName("muted")
            right.addWidget(time_label, 0, Qt.AlignRight)
            layout.addLayout(right)
            self.list_layout.addWidget(row)

        self.list_layout.addStretch(1)

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
