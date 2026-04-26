# Zero-Bloat JQ Filter Example (LangGraph)

This example demonstrates how to build an autonomous agent using **LangChain** and **LangGraph** that avoids context window bloat by offloading data processing to a remote Wasm tool via the Neonia MCP Gateway.

## The Problem: Token Bloat

Traditionally, if an AI agent needs to find a specific value in a large 5MB JSON file, the framework will load the entire JSON into the LLM's context window. This approach:

1. Burns through thousands of tokens unnecessarily.
2. Increases latency drastically.
3. Rapidly approaches the context window limit, leading to "amnesia".

## The Neonia Solution: Remote JQ Execution

Instead of reading the raw JSON file, this agent leverages the Neonia MCP Gateway.
It explicitly connects and binds the `neo_data_jq_filter` capability to run a Wasm-powered **JQ filter** on the remote server.

The LLM never sees the massive JSON. It only sees the final, extracted result (e.g., `$651,758.23`).

### Impact

- **Tokens Saved:** ~50,000+ per request
- **Execution Speed:** Near instant, thanks to isolated Wasm modules

## How It Works

1. The agent connects to `mcp.neonia.io/mcp?tools=neo_data_jq_filter`.
2. It dynamically wraps the MCP tool into a LangChain `@tool` instance.
3. LangGraph builds a reactive agent (`create_agent`) equipped with this tool.
4. When asked to calculate the total carts value, the agent intelligently calls the remote tool instead of loading the massive JSON locally.

## Setup

1. Install dependencies using `uv`:

   ```bash
   uv sync
   ```

2. Create a `.env` file with your API keys:

   ```env
   OPENROUTER_API_KEY="your-openrouter-key"
   NEONIA_API_KEY="your-neonia-key"
   ```

3. Run the agent:

   ```bash
   uv run python agent.py
   ```
