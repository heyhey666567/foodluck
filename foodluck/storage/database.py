"""SQLite-backed persistence for favorites, exclusions, history, and settings."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Set

from foodluck.models import (
    DrawMode,
    HistoryEntry,
    Restaurant,
    SavedRestaurant,
)

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    restaurant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,
    distance_km REAL NOT NULL,
    address TEXT,
    price_hkd INTEGER,
    is_open INTEGER,
    is_mock INTEGER NOT NULL DEFAULT 1,
    source_label TEXT NOT NULL DEFAULT '内置模拟数据',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exclusions (
    restaurant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,
    distance_km REAL NOT NULL,
    address TEXT,
    price_hkd INTEGER,
    is_open INTEGER,
    is_mock INTEGER NOT NULL DEFAULT 1,
    source_label TEXT NOT NULL DEFAULT '内置模拟数据',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,
    distance_km REAL NOT NULL,
    address TEXT,
    price_hkd INTEGER,
    is_open INTEGER,
    is_mock INTEGER NOT NULL DEFAULT 1,
    source_label TEXT NOT NULL DEFAULT '内置模拟数据',
    mode TEXT NOT NULL,
    confirmed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_confirmed_at
    ON history(confirmed_at DESC);
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _restaurant_from_row(row: sqlite3.Row) -> Restaurant:
    is_open = row["is_open"]
    source_label = (
        row["source_label"]
        if "source_label" in row.keys()
        else "内置模拟数据"
    )
    return Restaurant(
        id=row["restaurant_id"],
        name=row["name"],
        cuisine=row["cuisine"],
        distance_km=float(row["distance_km"]),
        address=row["address"],
        price_hkd=row["price_hkd"],
        is_open=None if is_open is None else bool(is_open),
        is_mock=bool(row["is_mock"]),
        source_label=source_label,
    )


class Database:
    """A tiny repository that opens short-lived SQLite connections.

    No connection is kept open, which keeps the GUI responsive and makes the
    store easy to test. Writes are committed per operation.
    """

    def __init__(self, path):
        self.path = Path(path).expanduser()
        self._initialized = False

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(_SCHEMA)
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    "数据库版本（{}）高于当前程序支持的版本（{}）。".format(
                        version, SCHEMA_VERSION
                    )
                )
            if version < SCHEMA_VERSION:
                self._migrate(connection, version)
                connection.execute("PRAGMA user_version = {}".format(SCHEMA_VERSION))
        self._initialized = True

    @staticmethod
    def _migrate(connection: sqlite3.Connection, from_version: int) -> None:
        if from_version < 2:
            for table in ("favorites", "exclusions", "history"):
                columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info({})".format(table)
                    ).fetchall()
                }
                if "source_label" not in columns:
                    connection.execute(
                        "ALTER TABLE {} ADD COLUMN source_label TEXT NOT NULL "
                        "DEFAULT '内置模拟数据'".format(table)
                    )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------
    def add_favorite(self, restaurant: Restaurant) -> None:
        self._ensure_initialized()
        with self._connect() as connection:
            self._upsert_snapshot(connection, "favorites", restaurant, _utc_now())

    def remove_favorite(self, restaurant_id: str) -> bool:
        self._ensure_initialized()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM favorites WHERE restaurant_id = ?", (restaurant_id,)
            )
            return cursor.rowcount > 0

    def is_favorite(self, restaurant_id: str) -> bool:
        self._ensure_initialized()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM favorites WHERE restaurant_id = ?", (restaurant_id,)
            ).fetchone()
            return row is not None

    def favorite_ids(self) -> Set[str]:
        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute("SELECT restaurant_id FROM favorites").fetchall()
            return {row["restaurant_id"] for row in rows}

    def list_favorites(self) -> List[SavedRestaurant]:
        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM favorites ORDER BY created_at DESC, name ASC"
            ).fetchall()
        return [
            SavedRestaurant(
                restaurant=_restaurant_from_row(row),
                saved_at=_parse_iso(row["created_at"]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Exclusions
    # ------------------------------------------------------------------
    def add_exclusion(self, restaurant: Restaurant) -> None:
        self._ensure_initialized()
        with self._connect() as connection:
            self._upsert_snapshot(connection, "exclusions", restaurant, _utc_now())

    def remove_exclusion(self, restaurant_id: str) -> bool:
        self._ensure_initialized()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM exclusions WHERE restaurant_id = ?", (restaurant_id,)
            )
            return cursor.rowcount > 0

    def clear_exclusions(self) -> int:
        self._ensure_initialized()
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM exclusions")
            return max(cursor.rowcount, 0)

    def exclusion_ids(self) -> Set[str]:
        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute("SELECT restaurant_id FROM exclusions").fetchall()
            return {row["restaurant_id"] for row in rows}

    def list_exclusions(self) -> List[SavedRestaurant]:
        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM exclusions ORDER BY created_at DESC, name ASC"
            ).fetchall()
        return [
            SavedRestaurant(
                restaurant=_restaurant_from_row(row),
                saved_at=_parse_iso(row["created_at"]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def add_history(self, restaurant: Restaurant, mode: DrawMode) -> int:
        self._ensure_initialized()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO history (
                    restaurant_id, name, cuisine, distance_km, address,
                    price_hkd, is_open, is_mock, source_label, mode, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    restaurant.id,
                    restaurant.name,
                    restaurant.cuisine,
                    restaurant.distance_km,
                    restaurant.address,
                    restaurant.price_hkd,
                    None if restaurant.is_open is None else int(restaurant.is_open),
                    int(restaurant.is_mock),
                    restaurant.source_label,
                    mode.value,
                    _iso(_utc_now()),
                ),
            )
            return int(cursor.lastrowid)

    def list_history(self, limit: int = 100) -> List[HistoryEntry]:
        self._ensure_initialized()
        safe_limit = max(1, min(int(limit), 500))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM history ORDER BY confirmed_at DESC, id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            HistoryEntry(
                id=int(row["id"]),
                restaurant=_restaurant_from_row(row),
                mode=DrawMode.from_value(row["mode"]),
                confirmed_at=_parse_iso(row["confirmed_at"]),
            )
            for row in rows
        ]

    def clear_history(self) -> int:
        self._ensure_initialized()
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM history")
            return max(cursor.rowcount, 0)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        self._ensure_initialized()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row is not None else default

    def set_setting(self, key: str, value: str) -> None:
        self._ensure_initialized()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    def set_settings(self, values: Mapping[str, str]) -> None:
        self._ensure_initialized()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                [(key, str(value)) for key, value in values.items()],
            )

    def get_settings(self, keys: List[str], defaults: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        self._ensure_initialized()
        defaults = defaults or {}
        if not keys:
            return {}
        placeholders = ", ".join("?" for _ in keys)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM settings WHERE key IN ({})".format(placeholders),
                tuple(keys),
            ).fetchall()
        result = {key: defaults.get(key, "") for key in keys}
        result.update({row["key"]: row["value"] for row in rows})
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _upsert_snapshot(
        connection: sqlite3.Connection,
        table: str,
        restaurant: Restaurant,
        saved_at: datetime,
    ) -> None:
        if table not in {"favorites", "exclusions"}:  # defensive, never user input
            raise ValueError("Unsupported snapshot table")
        connection.execute(
            """
            INSERT INTO {table} (
                restaurant_id, name, cuisine, distance_km, address,
                price_hkd, is_open, is_mock, source_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(restaurant_id) DO UPDATE SET
                name = excluded.name,
                cuisine = excluded.cuisine,
                distance_km = excluded.distance_km,
                address = excluded.address,
                price_hkd = excluded.price_hkd,
                is_open = excluded.is_open,
                is_mock = excluded.is_mock,
                source_label = excluded.source_label
            """.format(table=table),
            (
                restaurant.id,
                restaurant.name,
                restaurant.cuisine,
                restaurant.distance_km,
                restaurant.address,
                restaurant.price_hkd,
                None if restaurant.is_open is None else int(restaurant.is_open),
                int(restaurant.is_mock),
                restaurant.source_label,
                _iso(saved_at),
            ),
        )
