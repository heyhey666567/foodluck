import sqlite3
from datetime import datetime, timezone

from foodluck.models import DrawMode, Restaurant
from foodluck.storage.database import Database


def _restaurant():
    return Restaurant(
        id="demo-test",
        name="测试小馆",
        cuisine="港式",
        distance_km=0.42,
        address=None,
        price_hkd=66,
        is_open=True,
        is_mock=True,
    )


def test_favorites_and_exclusions_roundtrip(database):
    restaurant = _restaurant()
    database.add_favorite(restaurant)
    database.add_exclusion(restaurant)

    assert database.is_favorite(restaurant.id)
    assert database.favorite_ids() == {restaurant.id}
    assert database.exclusion_ids() == {restaurant.id}

    favorite = database.list_favorites()[0]
    assert favorite.restaurant.name == "测试小馆"
    assert favorite.restaurant.address is None
    assert favorite.restaurant.is_mock is True
    assert isinstance(favorite.saved_at, datetime)

    assert database.remove_exclusion(restaurant.id) is True
    assert database.exclusion_ids() == set()
    assert database.remove_favorite(restaurant.id) is True
    assert database.favorite_ids() == set()


def test_data_survives_a_new_database_instance(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    first = Database(path)
    first.initialize()
    first.add_exclusion(_restaurant())
    first.set_setting("mode", "fate")

    second = Database(path)
    second.initialize()
    assert second.exclusion_ids() == {"demo-test"}
    assert second.get_setting("mode") == "fate"


def test_history_records_mode_and_snapshot(database):
    restaurant = _restaurant()
    history_id = database.add_history(restaurant, DrawMode.FATE)
    assert isinstance(history_id, int)

    entries = database.list_history()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.mode is DrawMode.FATE
    assert entry.restaurant.name == "测试小馆"
    assert entry.confirmed_at.tzinfo is not None
    assert entry.confirmed_at <= datetime.now(timezone.utc)
    assert database.clear_history() == 1
    assert database.list_history() == []


def test_history_is_latest_first(database):
    old = Restaurant("old", "旧店", "港式", 0.1)
    new = Restaurant("new", "新店", "日料", 0.2)
    database.add_history(old, DrawMode.NORMAL)
    database.add_history(new, DrawMode.NORMAL)
    assert [entry.restaurant.id for entry in database.list_history()] == ["new", "old"]


def test_settings_are_upserted(database):
    assert database.get_setting("radius_km", "1.0") == "1.0"
    database.set_setting("radius_km", "0.5")
    database.set_setting("radius_km", "2.0")
    assert database.get_setting("radius_km") == "2.0"
    database.set_settings({"mode": "fate", "cuisine": "川菜"})
    values = database.get_settings(
        ["mode", "cuisine", "missing"],
        {"missing": "fallback"},
    )
    assert values == {"mode": "fate", "cuisine": "川菜", "missing": "fallback"}


def test_restore_all_exclusions(database):
    database.add_exclusion(Restaurant("a", "A", "港式", 0.1))
    database.add_exclusion(Restaurant("b", "B", "川菜", 0.2))
    assert database.clear_exclusions() == 2
    assert database.exclusion_ids() == set()


def test_schema_v1_migrates_source_label(tmp_path):
    path = tmp_path / "v1.sqlite3"
    connection = sqlite3.connect(str(path))
    connection.executescript(
        """
        CREATE TABLE favorites (
            restaurant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            distance_km REAL NOT NULL,
            address TEXT,
            price_hkd INTEGER,
            is_open INTEGER,
            is_mock INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        PRAGMA user_version = 1;
        """
    )
    connection.commit()
    connection.close()

    database = Database(path)
    database.initialize()

    connection = sqlite3.connect(str(path))
    columns = [row[1] for row in connection.execute("PRAGMA table_info(favorites)")]
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    connection.close()
    assert "source_label" in columns
    assert version == 2
    assert database.get_setting("missing", "fallback") == "fallback"


def test_live_source_label_is_preserved(database):
    live = Restaurant(
        id="osm:node:1",
        name="真实餐厅",
        cuisine="港式",
        distance_km=0.2,
        is_mock=False,
        source_label="OpenStreetMap (Nominatim)",
    )
    database.add_favorite(live)
    database.add_exclusion(live)
    database.add_history(live, DrawMode.NORMAL)

    assert (
        database.list_favorites()[0].restaurant.source_label
        == "OpenStreetMap (Nominatim)"
    )
    assert (
        database.list_exclusions()[0].restaurant.source_label
        == "OpenStreetMap (Nominatim)"
    )
    assert (
        database.list_history()[0].restaurant.source_label
        == "OpenStreetMap (Nominatim)"
    )
    assert database.list_favorites()[0].restaurant.is_mock is False
