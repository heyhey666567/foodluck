from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from foodluck.storage.database import Database


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def database(tmp_path):
    store = Database(tmp_path / "foodluck-test.sqlite3")
    store.initialize()
    return store
