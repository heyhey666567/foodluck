"""Local, deterministic restaurant provider used by the demo mode."""

from __future__ import annotations

from typing import List, Sequence

from foodluck.data.mock_data import DEMO_RESTAURANTS
from foodluck.models import Restaurant, RestaurantQuery


class MockRestaurantProvider:
    """Search fictional restaurants without any network access.

    Distance values are authored around the Hong Kong Polytechnic University
    area. The free-text location is intentionally not geocoded in demo mode;
    the UI says so instead of implying that a real nearby search happened.
    """

    source_name = "内置模拟数据"
    is_mock = True
    supports_open_status = True
    supports_price = True
    requires_network = False

    def __init__(self, restaurants: Sequence[Restaurant] = DEMO_RESTAURANTS):
        self._restaurants = tuple(restaurants)

    @property
    def restaurants(self) -> tuple:
        return self._restaurants

    def search(self, query: RestaurantQuery) -> List[Restaurant]:
        if query.radius_km <= 0:
            return []
        results = [
            restaurant
            for restaurant in self._restaurants
            if restaurant.distance_km <= query.radius_km
            and (not query.cuisine or restaurant.cuisine == query.cuisine)
            and restaurant.matches_budget(query.budget)
            and (not query.open_only or restaurant.is_open is True)
        ]
        return sorted(results, key=lambda item: (item.distance_km, item.name))
