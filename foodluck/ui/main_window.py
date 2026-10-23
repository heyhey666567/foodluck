"""Main application window and orchestration between UI, data, and SQLite."""

from __future__ import annotations

import sqlite3
from collections import Counter
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from foodluck import __version__
from foodluck.data.mock_provider import MockRestaurantProvider
from foodluck.data.overpass import OverpassProvider
from foodluck.data.provider import RestaurantProvider, RestaurantProviderError
from foodluck.logic.draw import DrawEngine, EmptyCandidatePool
from foodluck.models import (
    DEFAULT_LOCATION,
    DataSource,
    DrawMode,
    Restaurant,
    RestaurantQuery,
)
from foodluck.services.live_search import LiveRestaurantSearch
from foodluck.storage.database import Database
from foodluck.ui.dialogs import ExcludedDialog
from foodluck.ui.pages import DrawPage, FavoritesPage, HistoryPage
from foodluck.ui.widgets import Badge, NavButton, Toast, muted_divider


class MainWindow(QMainWindow):
    SETTING_DEFAULTS = {
        "location": DEFAULT_LOCATION,
        "radius_km": "1.0",
        "cuisine": "",
        "budget": "any",
        "open_only": "0",
        "mode": "normal",
        "data_source": "demo",
        "live_location_name": "香港理工大学",
        "live_latitude": "22.304500",
        "live_longitude": "114.179500",
    }

    def __init__(
        self,
        database: Database,
        provider: Optional[RestaurantProvider] = None,
        overpass_provider: Optional[OverpassProvider] = None,
        live_search: Optional[LiveRestaurantSearch] = None,
    ):
        super().__init__()
        self.database = database
        self.database.initialize()
        self.mock_provider = provider or MockRestaurantProvider()
        self.overpass_provider = overpass_provider or OverpassProvider()
        self.live_search = live_search or LiveRestaurantSearch(
            self.overpass_provider, parent=self
        )
        self.provider = self.mock_provider
        self.engine = DrawEngine()
        self._result: Optional[Restaurant] = None
        self._pending_result: Optional[Restaurant] = None
        self._confirmed = False
        self._last_error: Optional[str] = None
        self._last_candidates: List[Restaurant] = []
        self._nav_buttons: List[NavButton] = []
        self._live_raw_results: Optional[List[Restaurant]] = None
        self._live_loaded_key: Optional[Tuple[float, float, float]] = None
        self._pending_live_key: Optional[Tuple[float, float, float]] = None
        self._pending_draw_after_search = False

        self._finish_timer = QTimer(self)
        self._finish_timer.setSingleShot(True)
        self._finish_timer.timeout.connect(self._finish_draw)
        self._exclude_timer = QTimer(self)
        self._exclude_timer.setSingleShot(True)
        self._exclude_timer.timeout.connect(self._draw_after_exclusion)
        self._settings_timer = QTimer(self)
        self._settings_timer.setSingleShot(True)
        self._settings_timer.setInterval(320)
        self._settings_timer.timeout.connect(self._flush_settings)

        self.setWindowTitle("食运 FoodLuck")
        self.resize(1280, 860)
        self.setMinimumSize(1120, 760)
        self._build()
        self._connect()
        self._load_settings()
        self._refresh_candidates()
        self._refresh_favorites()
        self._refresh_history()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.draw_page = DrawPage()
        self.favorites_page = FavoritesPage()
        self.history_page = HistoryPage()
        self.stack.addWidget(self.draw_page)
        self.stack.addWidget(self.favorites_page)
        self.stack.addWidget(self.history_page)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.toast = Toast(root)
        self._position_toast()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(222)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(7)

        brand = QHBoxLayout()
        brand.setSpacing(11)
        mark = QLabel("食")
        mark.setObjectName("logoMark")
        mark.setFixedSize(48, 48)
        mark.setAlignment(Qt.AlignCenter)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_name = QLabel("食运")
        brand_name.setObjectName("brandName")
        brand_caption = QLabel("FOODLUCK")
        brand_caption.setObjectName("brandCaption")
        brand_text.addWidget(brand_name)
        brand_text.addWidget(brand_caption)
        brand.addWidget(mark)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        layout.addLayout(brand)
        layout.addSpacing(17)
        layout.addWidget(muted_divider())
        layout.addSpacing(14)

        nav_section = QLabel("探索")
        nav_section.setObjectName("navSection")
        layout.addWidget(nav_section)
        layout.addSpacing(2)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, text in enumerate(("抽签", "收藏", "历史")):
            button = NavButton(text)
            self.nav_group.addButton(button)
            button.clicked.connect(
                lambda _checked=False, page_index=index: self._switch_page(page_index)
            )
            layout.addWidget(button)
            self._nav_buttons.append(button)
        self._nav_buttons[0].setChecked(True)
        layout.addStretch(1)

        side_note = QFrame()
        side_note.setObjectName("sideNote")
        note_layout = QVBoxLayout(side_note)
        note_layout.setContentsMargins(12, 11, 12, 11)
        note_layout.setSpacing(4)
        note_title = QLabel("本地优先")
        note_title.setObjectName("sideNoteTitle")
        note_text = QLabel("收藏与历史仅保存在本机")
        note_text.setObjectName("helper")
        note_text.setWordWrap(True)
        note_layout.addWidget(note_title)
        note_layout.addWidget(note_text)
        layout.addWidget(side_note)
        layout.addSpacing(10)

        demo_row = QHBoxLayout()
        demo_row.setSpacing(6)
        self.data_badge = Badge("测试数据", "accent")
        version = QLabel("v{}".format(__version__))
        version.setObjectName("helper")
        demo_row.addWidget(self.data_badge)
        demo_row.addStretch(1)
        demo_row.addWidget(version)
        layout.addLayout(demo_row)
        return sidebar

    def _connect(self) -> None:
        page = self.draw_page
        page.draw_requested.connect(lambda: self._start_draw(animate=True))
        page.reroll_requested.connect(lambda: self._start_draw(animate=True))
        page.confirm_requested.connect(self.confirm_current)
        page.favorite_requested.connect(self.toggle_favorite_current)
        page.exclude_requested.connect(self.exclude_current)
        page.filters_changed.connect(self._on_filters_changed)
        page.mode_changed.connect(self._on_mode_changed)
        page.source_changed.connect(self._on_source_changed)
        page.manage_exclusions_requested.connect(self._open_excluded_dialog)
        self.favorites_page.remove_requested.connect(self._remove_favorite)
        self.history_page.clear_requested.connect(self._clear_history)
        self.live_search.succeeded.connect(self._on_live_search_succeeded)
        self.live_search.failed.connect(self._on_live_search_failed)

    # ------------------------------------------------------------------
    # Public-ish state used by tests and other UI code
    # ------------------------------------------------------------------
    @property
    def current_result(self) -> Optional[Restaurant]:
        return self._result

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def current_mode(self) -> DrawMode:
        return self.draw_page.mode

    # ------------------------------------------------------------------
    # Settings and filters
    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        values = self.database.get_settings(
            list(self.SETTING_DEFAULTS.keys()), self.SETTING_DEFAULTS
        )
        self.draw_page.apply_settings(values)
        self._apply_source_context(self.draw_page.source)
        self.draw_page.render_idle()

    def _apply_source_context(self, source: DataSource) -> None:
        self.provider = (
            self.mock_provider if source is DataSource.DEMO else self.overpass_provider
        )
        if source is DataSource.DEMO:
            self.data_badge.setText("测试数据")
            self.data_badge.set_tone("accent")
        else:
            self.data_badge.setText("OSM 实时")
            self.data_badge.set_tone("mint")

    def _queue_settings(self) -> None:
        self._settings_timer.start()

    def _flush_settings(self) -> None:
        self._settings_timer.stop()
        try:
            self.database.set_settings(self.draw_page.settings_snapshot())
        except Exception as exc:
            self._show_toast("设置保存失败：{}".format(exc))

    def _on_filters_changed(self) -> None:
        if self.draw_page.rolling or self.draw_page.searching:
            return
        self._queue_settings()
        _results, available, _excluded = self._refresh_candidates()
        available_ids = {restaurant.id for restaurant in available}
        if self._result is not None and self._result.id not in available_ids:
            self._result = None
            self._confirmed = False
            self.draw_page.render_idle()
            self._show_toast("筛选已更新，请重新抽签")
        elif self._result is None and self._last_error and available:
            self._last_error = None
            self.draw_page.render_idle()
        elif self.draw_page.source is DataSource.LIVE:
            query = self.draw_page.query()
            if self._live_key(query) != self._live_loaded_key and self._result is None:
                self._last_error = None
                self.draw_page.render_idle()

    def _on_mode_changed(self, mode: DrawMode) -> None:
        self._queue_settings()
        if self._result is not None and not self.draw_page.rolling:
            self._render_current()

    def _on_source_changed(self, source: DataSource) -> None:
        self.live_search.cancel()
        self._pending_draw_after_search = False
        self._pending_live_key = None
        self._live_raw_results = None
        self._live_loaded_key = None
        self._result = None
        self._confirmed = False
        self._last_error = None
        self._apply_source_context(source)
        self.draw_page.set_source(source)
        self.draw_page.render_idle()
        self._queue_settings()
        self._refresh_candidates()
        if source is DataSource.DEMO:
            self._show_toast("已切换到演示数据")
        else:
            self._show_toast("真实模式：点击「搜索并抽签」联网查询附近餐厅")

    # ------------------------------------------------------------------
    # Candidate pool
    # ------------------------------------------------------------------
    def _live_key(self, query: RestaurantQuery) -> Optional[Tuple[float, float, float]]:
        if query.latitude is None or query.longitude is None:
            return None
        return (
            round(query.latitude, 5),
            round(query.longitude, 5),
            round(query.radius_km, 3),
        )

    @staticmethod
    def _filter_live_results(
        results: List[Restaurant], query: RestaurantQuery
    ) -> List[Restaurant]:
        if not query.cuisine:
            return list(results)
        return [restaurant for restaurant in results if restaurant.cuisine == query.cuisine]

    def _refresh_candidates(self) -> Tuple[List[Restaurant], List[Restaurant], set]:
        query = self.draw_page.query()
        excluded_ids = self.database.exclusion_ids()

        if self.draw_page.source is DataSource.LIVE:
            key = self._live_key(query)
            if (
                key is None
                or self._live_loaded_key != key
                or self._live_raw_results is None
            ):
                self._last_candidates = []
                self.draw_page.set_pool_unsearched(query.location)
                self.draw_page.set_excluded_count(len(excluded_ids))
                return [], [], excluded_ids
            results = self._filter_live_results(self._live_raw_results, query)
            open_known = False
        else:
            try:
                results = self.provider.search(query)
            except RestaurantProviderError as exc:
                self._last_candidates = []
                self.draw_page.set_pool_counts(0, 0, 0, 0, {})
                self.draw_page.set_excluded_count(len(excluded_ids))
                self._show_toast("餐厅数据读取失败：{}".format(exc))
                return [], [], excluded_ids
            except Exception:
                self._last_candidates = []
                self.draw_page.set_pool_counts(0, 0, 0, 0, {})
                self.draw_page.set_excluded_count(len(excluded_ids))
                self._show_toast("餐厅数据读取失败，请稍后重试。")
                return [], [], excluded_ids
            open_known = True

        available = [r for r in results if r.id not in excluded_ids]
        excluded_in_filter = len(results) - len(available)
        open_count = sum(1 for r in available if r.is_open is True)
        cuisine_counts = Counter(r.cuisine for r in available)
        self.draw_page.set_pool_counts(
            total=len(results),
            available=len(available),
            excluded=excluded_in_filter,
            open_count=open_count,
            cuisine_counts=dict(cuisine_counts),
            open_known=open_known,
        )
        self.draw_page.set_excluded_count(len(excluded_ids))
        self._last_candidates = results
        return results, available, excluded_ids

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _start_draw(self, animate: bool = True) -> Optional[Restaurant]:
        if self.draw_page.rolling or self.draw_page.searching:
            return None

        if self.draw_page.source is DataSource.LIVE:
            query = self.draw_page.query()
            key = self._live_key(query)
            if key is None:
                message = "没有可用的地点坐标。请重新选择地点或输入坐标。"
                self._last_error = message
                self.draw_page.show_error(message)
                return None
            if self._live_loaded_key != key or self._live_raw_results is None:
                self._begin_live_search(query, key)
                return None

        self._finish_timer.stop()
        self._pending_result = None
        results, available, excluded_ids = self._refresh_candidates()

        if not available:
            if results:
                message = (
                    "本筛选内的餐厅都已被暂时排除。打开「查看并恢复」把想吃的店放回候选池。"
                )
            else:
                message = (
                    "当前筛选下没有符合条件的餐厅。请放宽搜索范围、更换菜系或预算后再试。"
                )
            self._last_error = message
            self._result = None
            self._confirmed = False
            self.draw_page.show_error(message)
            self._show_toast("候选池为空，暂时抽不出结果")
            return None

        try:
            result = self.engine.draw(results, excluded_ids)
        except EmptyCandidatePool:
            message = "当前筛选下没有可抽取的餐厅。"
            self._last_error = message
            self.draw_page.show_error(message)
            return None

        self._last_error = None
        self._result = result
        self._confirmed = False
        if animate:
            self._pending_result = result
            self.draw_page.begin_roll([restaurant.name for restaurant in available])
            self._finish_timer.start(860)
        else:
            self._render_current()
        return result

    def _finish_draw(self) -> None:
        result = self._pending_result
        self._pending_result = None
        if result is None:
            return
        self._result = result
        self._render_current()

    def _begin_live_search(
        self,
        query: RestaurantQuery,
        key: Tuple[float, float, float],
    ) -> None:
        if self.live_search.busy:
            return
        self._pending_live_key = key
        self._pending_draw_after_search = True
        self._last_error = None
        self.draw_page.begin_search(query.location, query.radius_km)
        self.live_search.start(query)

    def _on_live_search_succeeded(self, results) -> None:
        if self.draw_page.source is not DataSource.LIVE:
            return
        self._live_raw_results = list(results)
        self._live_loaded_key = self._pending_live_key
        self._pending_live_key = None
        self._pending_draw_after_search = False
        self.draw_page.end_search()
        self._last_error = None
        if not self._live_raw_results:
            self._live_loaded_key = None
            query = self.draw_page.query()
            message = (
                "OpenStreetMap 在「{}」周边 {:g} 公里内没有找到餐厅。"
                "可以扩大搜索范围或换一个地点。".format(
                    query.location, query.radius_km
                )
            )
            self._last_error = message
            self.draw_page.show_error(message)
            self._show_toast("附近没有找到真实餐厅")
            return
        self._show_toast("已找到 {} 家真实餐厅".format(len(self._live_raw_results)))
        self._start_draw(animate=True)

    def _on_live_search_failed(self, message: str) -> None:
        if self.draw_page.source is not DataSource.LIVE:
            return
        self._pending_draw_after_search = False
        self._pending_live_key = None
        self.draw_page.end_search()
        self._result = None
        self._confirmed = False
        self._last_error = message
        self.draw_page.show_error(message)
        self._show_toast("真实搜索失败")

    def draw_now(self, animate: bool = False) -> Optional[Restaurant]:
        """Programmatic entry point, useful for smoke tests."""

        return self._start_draw(animate=animate)

    def _render_current(self) -> None:
        if self._result is None:
            return
        try:
            favorite = self.database.is_favorite(self._result.id)
        except sqlite3.Error:
            favorite = False
        self.draw_page.render_result(
            self._result,
            favorite=favorite,
            confirmed=self._confirmed,
            mode=self.draw_page.mode,
        )

    def confirm_current(self) -> bool:
        if (
            self._result is None
            or self._confirmed
            or self.draw_page.rolling
            or self.draw_page.searching
        ):
            return False
        try:
            self.database.add_history(self._result, self.draw_page.mode)
        except Exception as exc:
            self._show_toast("记录保存失败：{}".format(exc))
            return False
        self._confirmed = True
        self.draw_page.mark_confirmed()
        self._refresh_history()
        self._show_toast("已记入餐单：{}".format(self._result.name))
        return True

    def toggle_favorite_current(self) -> bool:
        if self._result is None:
            return False
        try:
            favorite = self.database.is_favorite(self._result.id)
            if favorite:
                self.database.remove_favorite(self._result.id)
            else:
                self.database.add_favorite(self._result)
        except Exception as exc:
            self._show_toast("收藏保存失败：{}".format(exc))
            return False

        favorite = not favorite
        self.draw_page.set_favorite(favorite)
        self._refresh_favorites()
        self._show_toast(
            "已收藏 {}".format(self._result.name)
            if favorite
            else "已取消收藏 {}".format(self._result.name)
        )
        return favorite

    def exclude_current(self) -> bool:
        if (
            self._result is None
            or self.draw_page.rolling
            or self.draw_page.searching
        ):
            return False
        restaurant = self._result
        try:
            self.database.add_exclusion(restaurant)
        except Exception as exc:
            self._show_toast("排除失败：{}".format(exc))
            return False

        self._result = None
        self._confirmed = False
        self._pending_result = None
        self.draw_page.render_idle()
        _results, available, _excluded = self._refresh_candidates()
        self._show_toast("已暂时排除「{}」".format(restaurant.name))
        if available:
            self._exclude_timer.start(280)
        else:
            message = "所有符合条件的餐厅都被排除了。请恢复一些餐厅后再抽签。"
            self._last_error = message
            self.draw_page.show_error(message)
        return True

    def _draw_after_exclusion(self) -> None:
        if not self.draw_page.rolling and not self.draw_page.searching:
            self._start_draw(animate=True)

    def _open_excluded_dialog(self) -> None:
        if self.draw_page.rolling or self.draw_page.searching:
            return
        dialog = ExcludedDialog(self.database, self)
        dialog.changed.connect(self._on_exclusions_changed)
        dialog.exec()
        self._refresh_candidates()

    def _on_exclusions_changed(self) -> None:
        _results, available, _excluded = self._refresh_candidates()
        if self._result is None and self._last_error and available:
            self._last_error = None
            self.draw_page.render_idle()
        self._position_toast()

    # ------------------------------------------------------------------
    # Lists and navigation
    # ------------------------------------------------------------------
    def _refresh_favorites(self) -> None:
        try:
            self.favorites_page.render(self.database.list_favorites())
        except Exception as exc:
            self._show_toast("收藏读取失败：{}".format(exc))

    def _refresh_history(self) -> None:
        try:
            self.history_page.render(self.database.list_history())
        except Exception as exc:
            self._show_toast("历史读取失败：{}".format(exc))

    def _remove_favorite(self, restaurant_id: str) -> None:
        try:
            self.database.remove_favorite(restaurant_id)
        except Exception as exc:
            self._show_toast("取消收藏失败：{}".format(exc))
            return
        if self._result is not None and self._result.id == restaurant_id:
            self.draw_page.set_favorite(False)
        self._refresh_favorites()
        self._show_toast("已移出收藏")

    def _clear_history(self) -> None:
        entries = self.database.list_history(limit=1)
        if not entries:
            return
        box = QMessageBox(self)
        box.setWindowTitle("清空用餐记录")
        box.setText("确定要清空所有用餐记录吗？")
        box.setInformativeText("此操作不可撤销；收藏与排除列表不会被删除。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        yes_button = box.button(QMessageBox.Yes)
        no_button = box.button(QMessageBox.No)
        if yes_button is not None:
            yes_button.setText("清空")
        if no_button is not None:
            no_button.setText("取消")
        if box.exec() != QMessageBox.Yes:
            return
        try:
            self.database.clear_history()
        except Exception as exc:
            self._show_toast("清空失败：{}".format(exc))
            return
        self._refresh_history()
        self._show_toast("用餐记录已清空")

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self._nav_buttons):
            button.setChecked(position == index)
        if index == 1:
            self._refresh_favorites()
        elif index == 2:
            self._refresh_history()
        if self.toast.isVisible():
            self.toast.raise_()

    # ------------------------------------------------------------------
    # Window helpers
    # ------------------------------------------------------------------
    def _show_toast(self, message: str) -> None:
        self.toast.show_message(message)
        self._position_toast()

    def _position_toast(self) -> None:
        if not hasattr(self, "toast"):
            return
        parent = self.toast.parentWidget()
        if parent is None:
            return
        x = max(0, (parent.width() - self.toast.width()) // 2)
        y = max(0, parent.height() - self.toast.height() - 28)
        self.toast.move(x, y)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._position_toast()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.live_search.cancel()
        self._finish_timer.stop()
        self._exclude_timer.stop()
        self._settings_timer.stop()
        self._flush_settings()
        super().closeEvent(event)
