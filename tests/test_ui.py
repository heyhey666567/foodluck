from __future__ import annotations

from typing import List

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest

from foodluck.models import DataSource, DrawMode, Restaurant, RestaurantQuery
from foodluck.ui.main_window import MainWindow
from foodluck.ui.theme import apply_theme


class StaticProvider:
    source_name = "测试数据"
    is_mock = True

    def __init__(self, restaurants: List[Restaurant]):
        self._restaurants = restaurants

    def search(self, query: RestaurantQuery) -> List[Restaurant]:
        return list(self._restaurants)


class FakeLiveSearch(QObject):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, results=None, error=None):
        super().__init__()
        self.results = results or []
        self.error = error
        self.busy = False
        self.calls = []
        self.cancel_count = 0

    def start(self, query):
        self.calls.append(query)
        self.busy = True
        if self.error:
            self.busy = False
            self.failed.emit(self.error)
            return
        self.busy = False
        self.succeeded.emit(list(self.results))

    def cancel(self):
        self.cancel_count += 1
        self.busy = False


def _live_restaurant():
    return Restaurant(
        id="osm:node:1",
        name="真实茶餐厅",
        cuisine="港式",
        distance_km=0.24,
        address="漆咸道北 88 号",
        price_hkd=None,
        is_open=None,
        is_mock=False,
        source_label="OpenStreetMap",
    )


@pytest.fixture
def window(qapp, database):
    apply_theme(qapp)
    main = MainWindow(database)
    main.show()
    qapp.processEvents()
    yield main
    main.close()
    qapp.processEvents()


def test_initial_window_and_draw_flow(window, database):
    assert window.draw_page.count_label.text() == "8"
    assert window.current_result is None

    result = window.draw_now(animate=False)
    assert result is not None
    assert window.current_result == result
    assert window.draw_page.name_label.text() == result.name
    assert window.draw_page.confirm_button.isVisible()

    assert window.confirm_current() is True
    entries = database.list_history()
    assert len(entries) == 1
    assert entries[0].restaurant.name == result.name
    assert window.draw_page.confirm_button.text() == "已记入餐单"

    assert window.confirm_current() is False
    assert len(database.list_history()) == 1


def test_animated_draw_completes_without_blocking(window, qapp):
    window.draw_page.draw_button.click()
    assert window.draw_page.rolling is True
    QTest.qWait(950)
    assert window.draw_page.rolling is False
    assert window.current_result is not None


def test_favorite_toggle_updates_page_and_database(window, database):
    result = window.draw_now(animate=False)
    assert result is not None
    assert window.toggle_favorite_current() is True
    assert database.favorite_ids() == {result.id}
    assert window.draw_page.favorite_button.isChecked()
    assert window.favorites_page.count_badge.text() == "1 家"

    assert window.toggle_favorite_current() is False
    assert database.favorite_ids() == set()
    assert window.favorites_page.count_badge.text() == "0 家"


def test_exclusion_and_recovery(window, database, qapp):
    result = window.draw_now(animate=False)
    assert result is not None
    assert window.exclude_current() is True
    window._exclude_timer.stop()
    assert database.exclusion_ids() == {result.id}
    assert window.current_result is None
    assert window.draw_page.excluded_count_label.text() == "1 家"

    database.clear_exclusions()
    window._refresh_candidates()
    assert window.draw_page.count_label.text() == "8"


def test_empty_result_is_explained(window, qapp):
    window.draw_page.radius_combo.setCurrentIndex(
        window.draw_page.radius_combo.findData(0.3)
    )
    window.draw_page.cuisine_combo.setCurrentIndex(
        window.draw_page.cuisine_combo.findData("川菜")
    )
    qapp.processEvents()
    assert window.draw_page.count_label.text() == "0"

    result = window.draw_now(animate=False)
    assert result is None
    assert window.current_result is None
    assert window.last_error is not None
    assert "没有" in window.last_error
    assert "再试一次" == window.draw_page.draw_button.text()


def test_all_candidates_excluded_is_explained(window, database):
    for restaurant in window.provider.restaurants:
        if restaurant.distance_km <= 1.0:
            database.add_exclusion(restaurant)
    result = window.draw_now(animate=False)
    assert result is None
    assert window.last_error is not None
    assert "排除" in window.last_error
    assert window.draw_page.count_label.text() == "0"


def test_fate_mode_hides_reroll(window):
    window.draw_page.set_mode(DrawMode.FATE)
    result = window.draw_now(animate=False)
    assert result is not None
    assert window.draw_page.reroll_button.isHidden()
    assert window.draw_page.state_label.text() == "命运已替你决定"


def test_missing_address_uses_placeholder(qapp, database):
    restaurant = Restaurant(
        id="only-one",
        name="资料缺失小馆",
        cuisine="港式",
        distance_km=0.2,
        address=None,
        price_hkd=None,
        is_open=None,
    )
    apply_theme(qapp)
    window = MainWindow(database, provider=StaticProvider([restaurant]))
    window.show()
    qapp.processEvents()
    result = window.draw_now(animate=False)
    assert result is not None
    assert window.draw_page.address_label.text() == "地址 · 暂无数据"
    assert window.draw_page.price_badge.text() == "价格暂无数据"
    assert window.draw_page.open_badge.text() == "营业状态暂无数据"
    window.close()
    qapp.processEvents()


def test_settings_are_persisted(window, database):
    window.draw_page.location_edit.setText("红磡站附近")
    window.draw_page.radius_combo.setCurrentIndex(
        window.draw_page.radius_combo.findData(0.5)
    )
    window._flush_settings()
    assert database.get_setting("location") == "红磡站附近"
    assert database.get_setting("radius_km") == "0.5"


def test_settings_restore_in_a_new_window(qapp, database):
    apply_theme(qapp)
    first = MainWindow(database)
    first.draw_page.location_edit.setText("黄埔附近")
    first.draw_page.radius_combo.setCurrentIndex(
        first.draw_page.radius_combo.findData(2.0)
    )
    first.draw_page.set_mode(DrawMode.FATE)
    first._flush_settings()
    first.close()
    qapp.processEvents()

    second = MainWindow(database)
    assert second.draw_page.location_edit.text() == "黄埔附近"
    assert second.draw_page.radius_combo.currentData() == 2.0
    assert second.current_mode is DrawMode.FATE
    second.close()
    qapp.processEvents()


def test_live_mode_toggles_controls_and_location(qapp, database):
    apply_theme(qapp)
    fake = FakeLiveSearch(results=[_live_restaurant()])
    window = MainWindow(database, live_search=fake)
    window.show()
    qapp.processEvents()

    window.draw_page.live_source_button.click()
    qapp.processEvents()
    assert window.draw_page.source is DataSource.LIVE
    assert window.draw_page.budget_combo.isEnabled() is False
    assert window.draw_page.open_check.isEnabled() is False
    assert window.draw_page.count_label.text() == "?"
    assert window.draw_page.draw_button.text() == "搜索并抽签"
    assert window.data_badge.text() == "OSM 实时"

    index = next(
        idx
        for idx in range(window.draw_page.live_location_combo.count())
        if window.draw_page.live_location_combo.itemData(idx).name == "理大学生宿舍"
    )
    window.draw_page.live_location_combo.setCurrentIndex(index)
    query = window.draw_page.query()
    assert query.location == "理大学生宿舍"
    assert query.latitude == pytest.approx(22.3037768)
    assert query.longitude == pytest.approx(114.185388)

    window.close()
    qapp.processEvents()


def test_live_search_success_draws_and_labels_source(qapp, database):
    apply_theme(qapp)
    fake = FakeLiveSearch(results=[_live_restaurant()])
    window = MainWindow(database, live_search=fake)
    window.show()
    qapp.processEvents()
    window.draw_page.live_source_button.click()
    window.draw_page.draw_button.click()
    window._finish_draw()
    qapp.processEvents()

    assert len(fake.calls) == 1
    assert fake.calls[0].latitude == pytest.approx(22.3045)
    assert window.current_result is not None
    assert window.current_result.name == "真实茶餐厅"
    assert window.draw_page.price_badge.text() == "价格暂无数据"
    assert "OpenStreetMap" in window.draw_page.source_note.text()
    assert window.draw_page.searching is False
    assert window.confirm_current() is True
    assert database.list_history()[0].restaurant.is_mock is False

    window.close()
    qapp.processEvents()


def test_live_search_failure_is_shown_without_blocking(qapp, database):
    apply_theme(qapp)
    fake = FakeLiveSearch(error="模拟网络错误")
    window = MainWindow(database, live_search=fake)
    window.show()
    qapp.processEvents()
    window.draw_page.live_source_button.click()
    window.draw_page.draw_button.click()
    qapp.processEvents()

    assert window.last_error == "模拟网络错误"
    assert window.current_result is None
    assert window.draw_page.searching is False
    assert window.draw_page.draw_button.text() == "重新搜索"
    assert window.draw_page.draw_button.isEnabled()

    window.close()
    qapp.processEvents()


def test_live_mode_is_persisted(qapp, database):
    apply_theme(qapp)
    first = MainWindow(database, live_search=FakeLiveSearch())
    first.draw_page.live_source_button.click()
    first._flush_settings()
    first.close()
    qapp.processEvents()

    second = MainWindow(database, live_search=FakeLiveSearch())
    assert second.draw_page.source is DataSource.LIVE
    assert second.draw_page.count_label.text() == "?"
    assert second.draw_page.draw_button.text() == "搜索并抽签"
    second.close()
    qapp.processEvents()
