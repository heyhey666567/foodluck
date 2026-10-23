from foodluck.data.mock_provider import MockRestaurantProvider
from foodluck.models import BudgetTier, RestaurantQuery


def test_mock_data_is_explicitly_marked_and_unique():
    provider = MockRestaurantProvider()
    assert provider.is_mock is True
    assert provider.source_name == "内置模拟数据"
    assert len({r.id for r in provider.restaurants}) == len(provider.restaurants)
    assert all(r.is_mock for r in provider.restaurants)
    assert all("测试地址" in r.address for r in provider.restaurants if r.address)


def test_default_radius_and_sorting():
    provider = MockRestaurantProvider()
    results = provider.search(RestaurantQuery())
    assert len(results) == 8
    assert [r.distance_km for r in results] == sorted(r.distance_km for r in results)
    assert all(r.distance_km <= 1.0 for r in results)


def test_radius_and_cuisine_filters():
    provider = MockRestaurantProvider()
    assert len(provider.search(RestaurantQuery(radius_km=0.3))) == 1
    savoury = provider.search(RestaurantQuery(radius_km=1.0, cuisine="川菜"))
    assert [r.name for r in savoury] == ["川味小馆"]
    assert provider.search(RestaurantQuery(radius_km=1.0, cuisine="素食"))[0].name == "青禾素食"


def test_budget_filter_excludes_unknown_prices():
    provider = MockRestaurantProvider()
    results = provider.search(
        RestaurantQuery(radius_km=1.0, budget=BudgetTier.FROM_50_TO_100)
    )
    assert len(results) == 6
    assert all(50 <= r.price_hkd <= 100 for r in results)


def test_open_only_filter():
    provider = MockRestaurantProvider()
    results = provider.search(RestaurantQuery(radius_km=1.0, open_only=True))
    assert len(results) == 7
    assert all(r.is_open is True for r in results)


def test_zero_radius_has_no_results():
    assert MockRestaurantProvider().search(RestaurantQuery(radius_km=0)) == []
