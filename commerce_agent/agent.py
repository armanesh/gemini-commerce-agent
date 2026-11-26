"""ADK agent on Gemini that answers shopper and store-staff questions about a
product catalog, using tools served over MCP."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

from commerce_agent import guardrails

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

INSTRUCTION = """You help shoppers and store staff of a Dutch retailer with questions about products,
prices, stock and promotions.

Rules:
- Use the tools for every fact. Never state a price, stock level, allergen or promotion you did not get from a tool in this conversation.
- Quote prices in EUR exactly as the tools return them. If a promotion applies, say so and name it.
- If the tools do not have the answer, say that plainly. Do not guess.
- Skincare: describe what the product is for, but give no medical advice.
- Allergens: only report what get_product returns, and suggest checking the pack.
- Keep answers short: two to four sentences, or a short list when comparing products.
Stores: AMS-CENTRAAL, UTR-HOOG-CATHARIJNE, RTM-LIJNBAAN."""


def catalog_toolset() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", "commerce_agent.mcp_server"],
                cwd=str(REPO_ROOT),
            ),
            timeout=20.0,
        ),
        tool_filter=list(guardrails.ALLOWED_TOOLS),
    )


def build_agent(model=DEFAULT_MODEL) -> LlmAgent:
    """Build the agent. Tests pass a scripted model; production uses Gemini."""
    return LlmAgent(
        name="commerce_assistant",
        model=model,
        description="Answers product, price, stock and promotion questions from the catalog.",
        instruction=INSTRUCTION,
        tools=[catalog_toolset()],
        before_tool_callback=guardrails.before_tool,
        after_tool_callback=guardrails.after_tool,
        after_model_callback=guardrails.after_model,
    )


root_agent = build_agent()
