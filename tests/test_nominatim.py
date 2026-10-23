from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtTest import QTest

from foodluck.data.nominatim import NominatimProvider
from foodluck.data.overpass import OverpassProvider
from foodluck.models import RestaurantQuery
from foodluck.services.live_search import LiveRestaurantSearch

NOMINATIM_SAMPLE = [
    {
        "place_id": 1,
        "osm_type": "node",
        "osm_id": 999,
        "lat": "22.3050",
        "lon": "114.1800",
        "category": "amenity",
        "type": "restaurant",
        "name": "测试真实餐厅",
        "display_name": "测试真实餐厅, 红磡, 香港",
        "extratags": {
            "cuisine": "cantonese",
            "addr:street": "漆咸道北",
            "addr:housenumber": "88",
        },
    },
    {
        "place_id": 2,
        "osm_type": "node",
        "osm_id": 1000,
        "lat": "22.4000",
        "lon": "114.3000",
        "category": "amenity",
        "type": "restaurant",
        "name": "范围外餐厅",
        "extratags": None,
    },
    {
        "place_id": 3,
        "osm_type": "node",
        "osm_id": 1001,
        "lat": "22.3051",
        "lon": "114.1801",
        "category": "shop",
        "type": "supermarket",
        "name": "不是餐厅",
        "extratags": None,
    },
]


class FallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self.send_response(502)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"overpass busy")

    def do_GET(self):  # noqa: N802 - http.server API
        body = json.dumps(NOMINATIM_SAMPLE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 - silence test server
        return


def test_nominatim_build_url_and_parse():
    provider = NominatimProvider()
    query = RestaurantQuery(
        location="香港理工大学",
        radius_km=1.0,
        latitude=22.3045,
        longitude=114.1795,
    )
    url = provider.build_url(query)
    assert "q=restaurant" in url
    assert "bounded=1" in url
    assert "viewbox=" in url

    results = provider.parse_payload(
        NOMINATIM_SAMPLE,
        origin_lat=22.3045,
        origin_lon=114.1795,
        radius_km=1.0,
    )
    assert len(results) == 1
    result = results[0]
    assert result.name == "测试真实餐厅"
    assert result.is_mock is False
    assert result.source_label == "OpenStreetMap (Nominatim)"
    assert result.cuisine == "港式"
    assert result.address == "漆咸道北 88"
    assert result.price_hkd is None
    assert result.is_open is None


def test_live_search_falls_back_to_nominatim(qapp):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = "http://127.0.0.1:{}".format(port)
    try:
        overpass = OverpassProvider(
            endpoint=base + "/overpass", timeout_seconds=2
        )
        nominatim = NominatimProvider(search_url=base + "/nominatim")
        search = LiveRestaurantSearch(
            overpass,
            nominatim,
            timeout_ms=2000,
        )
        state = {"results": None, "error": None}
        search.succeeded.connect(lambda results: state.update(results=results))
        search.failed.connect(lambda message: state.update(error=message))
        query = RestaurantQuery(
            location="香港理工大学",
            radius_km=1.0,
            latitude=22.3045,
            longitude=114.1795,
        )
        search.start(query)
        for _ in range(100):
            if state["results"] is not None or state["error"] is not None:
                break
            qapp.processEvents()
            QTest.qWait(20)
        assert state["error"] is None
        assert state["results"] is not None
        assert [restaurant.name for restaurant in state["results"]] == ["测试真实餐厅"]
        assert search.busy is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
