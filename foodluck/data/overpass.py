"""OpenStreetMap Overpass provider.

The parsing and query-building code is deliberately free of Qt so it can be
unit-tested, reused from a worker, or called from a script. The GUI uses an
asynchronous Qt client around this provider, so no HTTP call ever blocks the
event loop.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from foodluck.data.provider import RestaurantProviderError
from foodluck.models import Restaurant, RestaurantQuery

DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "FoodLuck/0.2 (PySide6 desktop prototype; OpenStreetMap nearby search)"
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESULTS = 200
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

_AMENITIES = ("restaurant", "cafe", "fast_food")

_CUISINE_MAP = {
    "cantonese": "港式",
    "dim_sum": "港式",
    "bbq": "港式",
    "hong_kong": "港式",
    "chinese": "中餐",
    "noodle": "中餐",
    "seafood": "中餐",
    "rice": "中餐",
    "sichuan": "川菜",
    "szechuan": "川菜",
    "japanese": "日料",
    "sushi": "日料",
    "ramen": "日料",
    "izakaya": "日料",
    "korean": "韩餐",
    "italian": "西式",
    "western": "西式",
    "american": "西式",
    "french": "西式",
    "burger": "西式",
    "pizza": "西式",
    "steak": "西式",
    "vegetarian": "素食",
    "vegan": "素食",
    "thai": "东南亚",
    "vietnamese": "东南亚",
    "malaysian": "东南亚",
    "indonesian": "东南亚",
    "singaporean": "东南亚",
    "asian": "东南亚",
    "indian": "印度菜",
    "coffee_shop": "咖啡轻食",
    "cafe": "咖啡轻食",
    "bakery": "咖啡轻食",
    "dessert": "咖啡轻食",
}


class OverpassProvider:
    """Query nearby food businesses from the public Overpass API."""

    source_name = "OpenStreetMap"
    is_mock = False
    supports_open_status = False
    supports_price = False
    requires_network = True

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ):
        self.endpoint = endpoint or os.environ.get(
            "FOODLUCK_OVERPASS_URL", DEFAULT_ENDPOINT
        )
        self.timeout_seconds = timeout_seconds

    def build_query(self, query: RestaurantQuery) -> str:
        if query.latitude is None or query.longitude is None:
            raise RestaurantProviderError("真实搜索缺少地点坐标，请重新选择地点。")
        radius_metres = max(50, min(int(round(query.radius_km * 1000)), 5000))
        latitude = query.latitude
        longitude = query.longitude
        return (
            '[out:json][timeout:20];\n'
            'nwr(around:{radius},{lat:.6f},{lon:.6f})'
            '["amenity"~"^({amenities})$"];\n'
            "out center tags 500;".format(
                radius=radius_metres,
                lat=latitude,
                lon=longitude,
                amenities="|".join(_AMENITIES),
            )
        )

    def search(self, query: RestaurantQuery) -> List[Restaurant]:
        """Synchronous fallback for tests/scripts.

        The GUI does not call this method; it uses ``LiveRestaurantSearch``
        with QNetworkAccessManager so the interface never blocks.
        """

        query_text = self.build_query(query)
        data = urllib.parse.urlencode({"data": query_text}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except Exception as exc:
            raise RestaurantProviderError(
                "无法连接 OpenStreetMap：{}".format(exc)
            ) from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise RestaurantProviderError("OpenStreetMap 返回的数据过大，请缩小搜索范围。")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RestaurantProviderError("OpenStreetMap 返回了无法解析的数据。") from exc

        restaurants = self.parse_payload(
            payload,
            origin_lat=query.latitude,
            origin_lon=query.longitude,
        )
        if query.cuisine:
            restaurants = [r for r in restaurants if r.cuisine == query.cuisine]
        return restaurants

    @staticmethod
    def parse_payload(
        payload: Dict,
        origin_lat: Optional[float],
        origin_lon: Optional[float],
    ) -> List[Restaurant]:
        if origin_lat is None or origin_lon is None:
            raise RestaurantProviderError("真实搜索缺少地点坐标。")
        if not isinstance(payload, dict):
            raise RestaurantProviderError("OpenStreetMap 返回格式不正确。")
        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise RestaurantProviderError("OpenStreetMap 返回中没有餐厅数据。")

        restaurants: List[Restaurant] = []
        seen = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict):
                continue
            latitude, longitude = _element_coordinates(element)
            if latitude is None or longitude is None:
                continue
            name = _first_text(tags, "name", "name:zh", "name:zh-Hant", "name:en")
            if not name:
                continue
            dedupe_key = (name, round(latitude, 5), round(longitude, 5))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            element_type = str(element.get("type") or "node")
            element_id = element.get("id")
            if element_id is None:
                continue
            distance = haversine_km(origin_lat, origin_lon, latitude, longitude)
            restaurants.append(
                Restaurant(
                    id="osm:{}:{}".format(element_type, element_id),
                    name=name,
                    cuisine=normalise_cuisine(tags.get("cuisine")),
                    distance_km=round(distance, 3),
                    address=_format_address(tags),
                    price_hkd=None,
                    is_open=None,
                    is_mock=False,
                    source_label="OpenStreetMap",
                )
            )

        restaurants.sort(key=lambda item: (item.distance_km, item.name))
        return restaurants[:MAX_RESULTS]


def _element_coordinates(element: Dict):
    latitude = element.get("lat")
    longitude = element.get("lon")
    if latitude is None or longitude is None:
        center = element.get("center")
        if isinstance(center, dict):
            latitude = center.get("lat")
            longitude = center.get("lon")
    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None, None


def _first_text(tags: Dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _format_address(tags: Dict) -> Optional[str]:
    full = _first_text(tags, "addr:full")
    if full:
        return full
    street = _first_text(tags, "addr:street")
    number = _first_text(tags, "addr:housenumber")
    if street and number:
        return "{} {}".format(street, number)
    if street:
        return street
    place = _first_text(tags, "addr:place", "addr:building", "addr:district")
    return place


def normalise_cuisine(raw) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "其他"
    tokens = [token.strip().lower() for token in re.split(r"[;,]", raw) if token.strip()]
    for token in tokens:
        if token in _CUISINE_MAP:
            return _CUISINE_MAP[token]
    return "其他"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(a))
