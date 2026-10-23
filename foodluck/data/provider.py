"""Restaurant provider contract.

The UI only talks to this interface. V0.1 ships a local mock provider; V0.2
adds an OpenStreetMap-backed provider without changing the interface.
"""

from __future__ import annotations

from typing import List, Protocol

from foodluck.models import Restaurant, RestaurantQuery


class RestaurantProviderError(RuntimeError):
    """A provider could not complete a search."""


class RestaurantProvider(Protocol):
    source_name: str
    is_mock: bool
    supports_open_status: bool
    supports_price: bool
    requires_network: bool

    def search(self, query: RestaurantQuery) -> List[Restaurant]:
        ...
