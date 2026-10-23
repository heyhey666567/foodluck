"""Nominatim fallback for real OpenStreetMap restaurant discovery.

The primary live source is Overpass. Public Overpass instances are sometimes
at capacity, so the GUI automatically retries a bounded Nominatim search. Both
services expose OpenStreetMap data under ODbL; this module never invents fields
that the source does not provide.
"""

from __future__ import annotations

import math
import os
import urllib.parse
from typing import Dict, List, Optional

from foodluck.data.overpass import haversine_km, normalise_cuisine
from foodluck.data.provider import RestaurantProviderError
from foodluck.models import Restaurant, RestaurantQuery

DEFAULT_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
MAX_RESULTS = 100


class NominatimProvider:
    source_name = "OpenStreetMap (Nominatim)"
    is_mock = False
    supports_open_status = False
    supports_price = False
    requires_network = True

    def __init__(self, search_url: Optional[str] = None, timeout_seconds: int = 8):
        self.search_url = search_url or os.environ.get(
            "FOODLUCK_NOMINATIM_URL", DEFAULT_SEARCH_URL
        )
        self.timeout_seconds = timeout_seconds

    def build_url(self, query: RestaurantQuery) -> str:
        if query.latitude is None or query.longitude is None:
            raise RestaurantProviderError("真实搜索缺少地点坐标。")
        radius = max(0.05, min(float(query.radius_km), 5.0))
        lat_delta = radius / 111.32
        lon_delta = radius / (111.32 * max(math.cos(math.radians(query.latitude)), 0.1))
        left = query.longitude - lon_delta
        right = query.longitude + lon_delta
        top = query.latitude + lat_delta
        bottom = query.latitude - lat_delta
        params = {
            "q": "restaurant",
            "format": "jsonv2",
            "limit": "50",
            "extratags": "1",
            "addressdetails": "1",
            "bounded": "1",
            "viewbox": "{:.6f},{:.6f},{:.6f},{:.6f}".format(
                left, top, right, bottom
            ),
            "accept-language": "zh-HK,zh,en",
        }
        return "{}?{}".format(self.search_url, urllib.parse.urlencode(params))

    @staticmethod
    def parse_payload(
        payload,
        origin_lat: float,
        origin_lon: float,
        radius_km: float,
    ) -> List[Restaurant]:
        if not isinstance(payload, list):
            raise RestaurantProviderError("Nominatim 返回格式不正确。")
        results: List[Restaurant] = []
        seen = set()
        for item in payload:
            if not isinstance(item, dict):
                continue
            category = item.get("category")
            place_type = item.get("type")
            if category not in (None, "amenity"):
                continue
            if place_type not in (None, "restaurant", "fast_food", "cafe"):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            try:
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            distance = haversine_km(origin_lat, origin_lon, latitude, longitude)
            if distance > radius_km + 0.02:
                continue
            osm_type = str(item.get("osm_type") or "node").lower()
            osm_id = item.get("osm_id")
            if osm_id is None:
                continue
            dedupe_key = (name.strip(), round(latitude, 5), round(longitude, 5))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            extratags = item.get("extratags")
            if not isinstance(extratags, dict):
                extratags = {}
            results.append(
                Restaurant(
                    id="osm:{}:{}".format(osm_type, osm_id),
                    name=name.strip(),
                    cuisine=normalise_cuisine(extratags.get("cuisine")),
                    distance_km=round(distance, 3),
                    address=_address_from_item(item, extratags),
                    price_hkd=None,
                    is_open=None,
                    is_mock=False,
                    source_label="OpenStreetMap (Nominatim)",
                )
            )
        results.sort(key=lambda restaurant: (restaurant.distance_km, restaurant.name))
        return results[:MAX_RESULTS]


def _address_from_item(item: Dict, extratags: Dict) -> Optional[str]:
    full = extratags.get("addr:full")
    if isinstance(full, str) and full.strip():
        return full.strip()
    street = extratags.get("addr:street")
    number = extratags.get("addr:housenumber")
    if isinstance(street, str) and street.strip():
        if isinstance(number, str) and number.strip():
            return "{} {}".format(street.strip(), number.strip())
        return street.strip()
    display_name = item.get("display_name")
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    return None
