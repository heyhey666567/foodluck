"""Pure draw logic, independent of Qt and SQLite."""

from __future__ import annotations

import random
from typing import Iterable, List, Optional, Sequence

from foodluck.models import Restaurant


class EmptyCandidatePool(RuntimeError):
    """No restaurant can be drawn with the current filters."""

    def __init__(self, message: str = "当前筛选下没有可抽取的餐厅。"):
        super().__init__(message)


class DrawEngine:
    """Pick one eligible restaurant with equal probability.

    Exclusion is a filter, not a weight: every remaining candidate has exactly
    the same chance to be drawn.
    """

    def __init__(self, rng: Optional[random.Random] = None):
        self._rng = rng or random.SystemRandom()

    def available(
        self,
        restaurants: Sequence[Restaurant],
        excluded_ids: Iterable[str],
    ) -> List[Restaurant]:
        blocked = set(excluded_ids)
        return [restaurant for restaurant in restaurants if restaurant.id not in blocked]

    def draw(
        self,
        restaurants: Sequence[Restaurant],
        excluded_ids: Iterable[str],
    ) -> Restaurant:
        candidates = self.available(restaurants, excluded_ids)
        if not candidates:
            raise EmptyCandidatePool()
        return self._rng.choice(candidates)
