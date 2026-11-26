import pytest

from commerce_agent import catalog


def test_search_ranks_by_keyword_match_and_filters():
    results = catalog.search_products("fragrance free sensitive skin", category="skincare")
    assert results[0]["sku"] == "SKN-102"
    assert all(r["category"] == "skincare" for r in results)


def test_search_respects_max_price_and_limit():
    results = catalog.search_products("vegan", max_price_eur=2.5, limit=2)
    assert len(results) <= 2
    assert all(r["price_eur"] <= 2.5 for r in results)


def test_search_does_not_expose_stock():
    assert all("stock" not in r for r in catalog.search_products("snack"))


def test_get_product_normalises_sku():
    assert catalog.get_product(" skn-101 ")["price_eur"] == 12.99


@pytest.mark.parametrize("bad", ["SKN101", "SK-101", "", "SKN-1011"])
def test_invalid_sku_is_rejected(bad):
    with pytest.raises(catalog.CatalogError):
        catalog.get_product(bad)


def test_unknown_sku_is_rejected():
    with pytest.raises(catalog.CatalogError):
        catalog.get_product("ZZZ-999")


def test_check_stock_single_and_all_stores():
    assert catalog.check_stock("SKN-101", "utr-hoog-catharijne")["units"] == 0
    assert set(catalog.check_stock("SKN-101")["units_by_store"]) == {"AMS-CENTRAAL", "UTR-HOOG-CATHARIJNE", "RTM-LIJNBAAN"}


def test_check_stock_unknown_store():
    with pytest.raises(catalog.CatalogError):
        catalog.check_stock("SKN-101", "PARIS")


def test_promotion_active_and_inactive():
    assert catalog.get_promotion("SKN-102") == {
        "sku": "SKN-102", "active": True, "type": "percent_off", "value": 25,
        "valid_until": "2026-12-31", "description": "25% off the cleanser",
    }
    assert catalog.get_promotion("SKN-101") == {"sku": "SKN-101", "active": False}
