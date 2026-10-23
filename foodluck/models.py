"""Domain models shared by the data, logic, storage, and UI layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

DEFAULT_LOCATION = "香港理工大学附近"
CUISINES = (
    "港式",
    "中餐",
    "川菜",
    "日料",
    "韩餐",
    "西式",
    "素食",
    "东南亚",
    "印度菜",
    "咖啡轻食",
    "其他",
)
RADIUS_OPTIONS = (0.3, 0.5, 1.0, 2.0)


class DataSource(str, Enum):
    """Where restaurant results come from."""

    DEMO = "demo"
    LIVE = "live"

    @property
    def label(self) -> str:
        return "演示数据" if self is DataSource.DEMO else "真实附近"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "DataSource":
        try:
            return cls(value)
        except (TypeError, ValueError):
            return cls.DEMO


@dataclass(frozen=True)
class Location:
    """A search origin with coordinates used by map-backed providers."""

    name: str
    latitude: float
    longitude: float


class DrawMode(str, Enum):
    """How strictly the result should be treated."""

    NORMAL = "normal"
    FATE = "fate"

    @property
    def label(self) -> str:
        return "普通模式" if self is DrawMode.NORMAL else "命运模式"

    @property
    def description(self) -> str:
        if self is DrawMode.FATE:
            return "第一次抽中就收手。排除仍随时可用。"
        return "可以重新抽签，直到出现让你心动的答案。"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "DrawMode":
        try:
            return cls(value)
        except (TypeError, ValueError):
            return cls.NORMAL


class BudgetTier(str, Enum):
    ANY = "any"
    UNDER_50 = "under_50"
    FROM_50_TO_100 = "50_to_100"
    OVER_100 = "over_100"

    @property
    def label(self) -> str:
        return {
            BudgetTier.ANY: "预算不限",
            BudgetTier.UNDER_50: "HK$50 以下",
            BudgetTier.FROM_50_TO_100: "HK$50–100",
            BudgetTier.OVER_100: "HK$100 以上",
        }[self]

    @classmethod
    def from_value(cls, value: Optional[str]) -> "BudgetTier":
        try:
            return cls(value)
        except (TypeError, ValueError):
            return cls.ANY


@dataclass(frozen=True)
class RestaurantQuery:
    """A provider-neutral restaurant search request.

    A future map-backed provider can translate the same object into an API
    request without changing the UI or the draw engine.
    """

    location: str = DEFAULT_LOCATION
    radius_km: float = 1.0
    cuisine: Optional[str] = None
    budget: BudgetTier = BudgetTier.ANY
    open_only: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(frozen=True)
class Restaurant:
    id: str
    name: str
    cuisine: str
    distance_km: float
    address: Optional[str] = None
    price_hkd: Optional[int] = None
    is_open: Optional[bool] = None
    is_mock: bool = True
    source_label: str = "内置模拟数据"

    @property
    def distance_label(self) -> str:
        if self.distance_km < 1:
            return "{} 米".format(round(self.distance_km * 1000))
        return "{:.1f} 公里".format(self.distance_km)

    @property
    def price_label(self) -> str:
        if self.price_hkd is None:
            return "价格暂无数据"
        return "人均 HK${}".format(self.price_hkd)

    @property
    def open_label(self) -> str:
        if self.is_open is None:
            return "营业状态暂无数据"
        return "营业中" if self.is_open else "休息中"

    @property
    def address_label(self) -> str:
        return self.address if self.address else "暂无数据"

    def matches_budget(self, budget: BudgetTier) -> bool:
        if budget is BudgetTier.ANY:
            return True
        if self.price_hkd is None:
            return False
        if budget is BudgetTier.UNDER_50:
            return self.price_hkd < 50
        if budget is BudgetTier.FROM_50_TO_100:
            return 50 <= self.price_hkd <= 100
        return self.price_hkd > 100


@dataclass(frozen=True)
class SavedRestaurant:
    """A favorite or exclusion snapshot loaded from SQLite."""

    restaurant: Restaurant
    saved_at: datetime


@dataclass(frozen=True)
class HistoryEntry:
    """A confirmed meal choice loaded from SQLite."""

    id: int
    restaurant: Restaurant
    mode: DrawMode
    confirmed_at: datetime


def display_or_placeholder(value: Optional[str]) -> str:
    """Never invent missing restaurant fields."""

    return value if value else "暂无数据"
