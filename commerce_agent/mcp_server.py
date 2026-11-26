"""MCP server exposing the catalog as read-only tools.

Run standalone with:  python -m commerce_agent.mcp_server
The agent starts it over stdio through ADK's McpToolset.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from commerce_agent import catalog

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)

server = MCPServer(
    name="commerce-catalog",
    instructions="Read-only product catalog: search, product details, store stock and promotions.",
)


def _safe(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except catalog.CatalogError as e:
        return {"error": str(e)}


@server.tool(annotations=READ_ONLY)
def search_products(query: str = "", category: str | None = None, max_price_eur: float | None = None, limit: int = 5) -> list[dict] | dict:
    """Search products by keywords (name, brand, tags). Optional category (skincare, haircare, snacks, drinks) and max price in EUR."""
    return _safe(catalog.search_products, query, category, max_price_eur, limit)


@server.tool(annotations=READ_ONLY)
def get_product(sku: str) -> dict:
    """Get name, brand, category, price in EUR, tags and allergens for one SKU (format ABC-123)."""
    return _safe(catalog.get_product, sku)


@server.tool(annotations=READ_ONLY)
def check_stock(sku: str, store: str | None = None) -> dict:
    """Units in stock for a SKU, for one store (AMS-CENTRAAL, UTR-HOOG-CATHARIJNE, RTM-LIJNBAAN) or all stores."""
    return _safe(catalog.check_stock, sku, store)


@server.tool(annotations=READ_ONLY)
def get_promotion(sku: str) -> dict:
    """Active promotion for a SKU, if any."""
    return _safe(catalog.get_promotion, sku)


TOOL_NAMES = ("search_products", "get_product", "check_stock", "get_promotion")

if __name__ == "__main__":
    server.run("stdio")
