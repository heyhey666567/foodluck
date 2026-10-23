"""Built-in search origins.

These coordinates are intentionally small, reviewed presets rather than a live
geocoder. V0.2 can therefore perform real nearby searches without depending on
a second public service. Users can still enter their own coordinates.
"""

from __future__ import annotations

from typing import Iterable, Optional

from foodluck.models import Location

LOCATION_PRESETS = (
    Location("香港理工大学", 22.3045, 114.1795),
    Location("理大学生宿舍", 22.3037768, 114.1853880),
    Location("红磡站", 22.3027, 114.1815),
    Location("黄埔花园", 22.3049, 114.1894),
    Location("何文田", 22.3094, 114.1825),
    Location("尖沙咀", 22.2988, 114.1722),
    Location("旺角", 22.3193, 114.1694),
    Location("土瓜湾", 22.3176, 114.1878),
)

_ALIASES = {
    "香港理工大学": ("香港理工大学附近", "理大", "polyu", "hong kong polytechnic university"),
    "理大学生宿舍": ("学生宿舍", "宿舍", "polyu student halls"),
    "红磡站": ("红磡", "hung hom", "hung hom station"),
    "黄埔花园": ("黄埔", "whampoa", "whampoa garden"),
    "何文田": ("ho man tin",),
    "尖沙咀": ("尖沙咀站", "tst", "tsim sha tsui"),
    "旺角": ("mong kok",),
    "土瓜湾": ("to kwa wan",),
}


def _normalise(value: str) -> str:
    return " ".join(value.strip().lower().split())


def find_location(name: Optional[str]) -> Optional[Location]:
    if not name:
        return None
    needle = _normalise(name)
    for location in LOCATION_PRESETS:
        candidates: Iterable[str] = (location.name,) + _ALIASES.get(location.name, ())
        if any(_normalise(candidate) == needle for candidate in candidates):
            return location
    return None
