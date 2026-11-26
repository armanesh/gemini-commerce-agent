"""Read-only access to the product catalog.

These functions are the single source of truth for prices, stock and
promotions. The MCP server exposes them as tools; the agent never sees the
raw file.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"
SKU_PATTERN = re.compile(r"^[A-Z]{3}-\d{3}$")


class CatalogError(ValueError):
    """Raised for invalid input, so the tool returns a clear error to the agent."""


@lru_cache(maxsize=1)
def load_catalog(path: str = str(CATALOG_PATH)) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _products() -> list[dict[str, Any]]:
    return load_catalog()["products"]


def _public(product: dict[str, Any]) -> dict[str, Any]:
    """Product fields the agent may see (stock is only exposed through check_stock)."""
    keys = ("sku", "name", "brand", "category", "price_eur", "tags", "allergens")
    return {k: product[k] for k in keys if k in product}


def validate_sku(sku: str) -> str:
    sku = (sku or "").strip().upper()
    if not SKU_PATTERN.match(sku):
        raise CatalogError(f"'{sku}' is not a valid SKU (expected format ABC-123).")
    return sku


def search_products(
    query: str = "",
    category: str | None = None,
    max_price_eur: float | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Keyword search over name, brand and tags, with optional filters."""
    words = [w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(w) > 1]
    limit = max(1, min(int(limit), 10))
    results = []
    for p in _products():
        if category and p["category"] != category.lower():
            continue
        if max_price_eur is not None and p["price_eur"] > float(max_price_eur):
            continue
        text = " ".join([p["name"], p["brand"], p["category"], *p.get("tags", [])]).lower()
        score = sum(1 for w in words if w in text) if words else 1
        if score > 0:
            results.append((score, p))
    results.sort(key=lambda r: (-r[0], r[1]["price_eur"]))
    return [_public(p) for _, p in results[:limit]]


def get_product(sku: str) -> dict[str, Any]:
    sku = validate_sku(sku)
    for p in _products():
        if p["sku"] == sku:
            return _public(p)
    raise CatalogError(f"No product with SKU {sku}.")


def check_stock(sku: str, store: str | None = None) -> dict[str, Any]:
    sku = validate_sku(sku)
    stores = load_catalog()["stores"]
    for p in _products():
        if p["sku"] == sku:
            if store:
                store = store.strip().upper()
                if store not in stores:
                    raise CatalogError(f"Unknown store '{store}'. Known stores: {', '.join(stores)}.")
                return {"sku": sku, "store": store, "units": p["stock"][store]}
            return {"sku": sku, "units_by_store": dict(p["stock"])}
    raise CatalogError(f"No product with SKU {sku}.")


def get_promotion(sku: str) -> dict[str, Any]:
    sku = validate_sku(sku)
    get_product(sku)  # raises if unknown
    for promo in load_catalog()["promotions"]:
        if promo["sku"] == sku:
            return {"sku": sku, "active": True, **{k: promo[k] for k in ("type", "value", "valid_until", "description")}}
    return {"sku": sku, "active": False}
