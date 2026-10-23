import pytest

from foodluck.data.locations import LOCATION_PRESETS, find_location
from foodluck.data.overpass import OverpassProvider
from foodluck.data.provider import RestaurantProviderError
from foodluck.models import DataSource, RestaurantQuery

SAMPLE_PAYLOAD = {
    "elements": [
        {
            "type": "node",
            "id": 1,
            "lat": 22.3050,
            "lon": 114.1800,
            "tags": {
                "name": "近處茶餐廳",
                "cuisine": "cantonese;western",
                "addr:street": "漆咸道北",
                "addr:housenumber": "88",
            },
        },
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 22.3060, "lon": 114.1810},
            "tags": {
                "name": "遠方壽司",
                "cuisine": "sushi",
                "addr:full": "測試大廈 1 樓",
            },
        },
        {
            "type": "node",
            "id": 3,
            "lat": 22.3045,
            "lon": 114.1795,
            "tags": {"amenity": "restaurant"},
        },
        {
            "type": "node",
            "id": 4,
            "lat": 22.3050,
            "lon": 114.1800,
            "tags": {"name": "近處茶餐廳", "cuisine": "cantonese"},
        },
        {
            "type": "relation",
            "id": 5,
            "center": {"lat": 22.3049, "lon": 114.1799},
            "tags": {"name": "轉角咖啡", "cuisine": "coffee_shop"},
        },
    ]
}


def test_query_contains_radius_coordinates_and_amenities():
    provider = OverpassProvider()
    query = RestaurantQuery(
        location="香港理工大学",
        radius_km=0.5,
        latitude=22.3045,
        longitude=114.1795,
    )
    text = provider.build_query(query)
    assert "around:500,22.304500,114.179500" in text
    assert "restaurant|cafe|fast_food" in text
    assert "out center tags" in text


def test_query_requires_coordinates():
    provider = OverpassProvider()
    with pytest.raises(RestaurantProviderError):
        provider.build_query(RestaurantQuery(location="香港理工大学"))


def test_parse_real_osm_payload():
    results = OverpassProvider.parse_payload(
        SAMPLE_PAYLOAD,
        origin_lat=22.3045,
        origin_lon=114.1795,
    )
    assert len(results) == 3
    assert [r.name for r in results] == ["轉角咖啡", "近處茶餐廳", "遠方壽司"]
    assert all(r.is_mock is False for r in results)
    assert all(r.source_label == "OpenStreetMap" for r in results)
    assert all(r.price_hkd is None for r in results)
    assert all(r.is_open is None for r in results)
    assert [r.cuisine for r in results] == ["咖啡轻食", "港式", "日料"]
    assert results[1].address == "漆咸道北 88"
    assert results[2].address == "測試大廈 1 樓"
    assert results[0].address is None
    assert results[0].id == "osm:relation:5"
    assert results[0].distance_km <= results[1].distance_km <= results[2].distance_km


def test_parse_skips_unnamed_and_bad_elements():
    results = OverpassProvider.parse_payload(
        {
            "elements": [
                {"type": "node", "id": 1, "tags": {"name": "无坐标"}},
                {"type": "node", "id": 2, "lat": 22.3, "lon": 114.1, "tags": {}},
                None,
                {"type": "node", "id": 3, "lat": 22.3, "lon": 114.1, "tags": {"name": "有效餐厅"}},
            ]
        },
        origin_lat=22.3045,
        origin_lon=114.1795,
    )
    assert [r.name for r in results] == ["有效餐厅"]


def test_bad_payload_raises_provider_error():
    with pytest.raises(RestaurantProviderError):
        OverpassProvider.parse_payload({}, 22.3, 114.1)
    with pytest.raises(RestaurantProviderError):
        OverpassProvider.parse_payload({"elements": []}, None, 114.1)


def test_location_presets_and_aliases():
    assert len(LOCATION_PRESETS) >= 6
    assert find_location("理大").name == "香港理工大学"
    assert find_location("学生宿舍").name == "理大学生宿舍"
    assert find_location("Hung Hom").name == "红磡站"
    assert find_location("不存在的地点") is None
    halls = find_location("理大学生宿舍")
    assert halls.latitude == pytest.approx(22.3037768)
    assert halls.longitude == pytest.approx(114.185388)


def test_data_source_fallback():
    assert DataSource.from_value("live") is DataSource.LIVE
    assert DataSource.from_value("garbage") is DataSource.DEMO
