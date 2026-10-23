from foodluck.models import (
    BudgetTier,
    DrawMode,
    Restaurant,
    display_or_placeholder,
)


def test_missing_fields_are_never_invented():
    restaurant = Restaurant(
        id="missing",
        name="无资料小馆",
        cuisine="港式",
        distance_km=0.42,
        address=None,
        price_hkd=None,
        is_open=None,
    )
    assert restaurant.address_label == "暂无数据"
    assert restaurant.price_label == "价格暂无数据"
    assert restaurant.open_label == "营业状态暂无数据"
    assert display_or_placeholder(None) == "暂无数据"
    assert display_or_placeholder("红磡") == "红磡"


def test_distance_formatting():
    assert Restaurant("a", "A", "港式", 0.185).distance_label == "185 米"
    assert Restaurant("b", "B", "港式", 1.05).distance_label == "1.1 公里"


def test_budget_matching_including_unknown_price():
    cheap = Restaurant("a", "A", "港式", 0.2, price_hkd=49)
    mid = Restaurant("b", "B", "港式", 0.2, price_hkd=50)
    upper = Restaurant("c", "C", "港式", 0.2, price_hkd=100)
    pricey = Restaurant("d", "D", "港式", 0.2, price_hkd=101)
    unknown = Restaurant("e", "E", "港式", 0.2, price_hkd=None)

    assert cheap.matches_budget(BudgetTier.UNDER_50)
    assert not mid.matches_budget(BudgetTier.UNDER_50)
    assert mid.matches_budget(BudgetTier.FROM_50_TO_100)
    assert upper.matches_budget(BudgetTier.FROM_50_TO_100)
    assert pricey.matches_budget(BudgetTier.OVER_100)
    assert unknown.matches_budget(BudgetTier.ANY)
    assert not unknown.matches_budget(BudgetTier.FROM_50_TO_100)


def test_enum_fallbacks():
    assert DrawMode.from_value("fate") is DrawMode.FATE
    assert DrawMode.from_value("nonsense") is DrawMode.NORMAL
    assert BudgetTier.from_value("50_to_100") is BudgetTier.FROM_50_TO_100
    assert BudgetTier.from_value(None) is BudgetTier.ANY
