import random

import pytest

from foodluck.logic.draw import DrawEngine, EmptyCandidatePool
from foodluck.models import Restaurant


def _restaurants():
    return [
        Restaurant("a", "A", "港式", 0.1),
        Restaurant("b", "B", "川菜", 0.2),
        Restaurant("c", "C", "日料", 0.3),
    ]


def test_draw_respects_exclusions():
    engine = DrawEngine(random.Random(1))
    excluded = {"a", "c"}
    for _ in range(20):
        assert engine.draw(_restaurants(), excluded).id == "b"


def test_draw_is_roughly_uniform():
    engine = DrawEngine(random.Random(2026))
    counts = {"a": 0, "b": 0, "c": 0}
    for _ in range(3000):
        counts[engine.draw(_restaurants(), set()).id] += 1
    assert set(counts) == {"a", "b", "c"}
    assert all(800 <= value <= 1200 for value in counts.values())


def test_empty_pool_raises_clear_error():
    engine = DrawEngine(random.Random(1))
    with pytest.raises(EmptyCandidatePool):
        engine.draw([], set())
    with pytest.raises(EmptyCandidatePool):
        engine.draw(_restaurants(), {"a", "b", "c"})


def test_available_does_not_mutate_input():
    restaurants = _restaurants()
    engine = DrawEngine(random.Random(1))
    available = engine.available(restaurants, {"b"})
    assert [r.id for r in available] == ["a", "c"]
    assert len(restaurants) == 3
