import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import ROOT


async def _session_calls():
    params = StdioServerParameters(command=sys.executable, args=["-m", "commerce_agent.mcp_server"], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            product = await session.call_tool("get_product", {"sku": "SNK-302"})
            bad = await session.call_tool("get_product", {"sku": "nope"})
            return tools, product, bad


def test_mcp_server_over_stdio():
    tools, product, bad = asyncio.run(asyncio.wait_for(_session_calls(), 30))
    names = {t.name for t in tools.tools}
    assert names == {"search_products", "get_product", "check_stock", "get_promotion"}
    assert all(t.annotations.read_only_hint for t in tools.tools)
    data = json.loads(product.content[0].text)
    assert data["allergens"] == ["nuts", "milk"]
    assert "not a valid SKU" in bad.content[0].text
