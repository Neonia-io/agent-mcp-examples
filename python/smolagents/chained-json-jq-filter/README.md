# Chained JSON JQ Filter Example (SmolAgents)

This example demonstrates how to build an autonomous agent using **SmolAgents** and **LiteLLM** that avoids context window bloat by offloading data processing to a remote Wasm tool via the Neonia MCP Gateway.

## The Problem: Token Bloat

Traditionally, if an AI agent needs to find a specific value in a large JSON file, the framework will load the entire JSON into the LLM's context window. This approach:

1. Burns through thousands of tokens unnecessarily.
2. Increases latency drastically.
3. Rapidly approaches the context window limit, leading to "amnesia".

## The Neonia Solution: Chained Data Execution

Instead of reading the raw JSON file, this agent leverages the Neonia MCP Gateway to chain two tools together:
1. `neo_web_json_fetch` to fetch the large JSON from a remote URL. The Gateway stores the payload securely and returns a `resource_uri` pointer along with its TypeScript schema.
2. `neo_data_jq_filter` to run a Wasm-powered **JQ filter** on the remote server using the `resource_uri` and a generated jq query.

The LLM never sees the massive JSON. It only sees the final, extracted result.

### Impact

- **Tokens Saved:** ~50,000+ per request
- **Execution Speed:** Near instant, thanks to isolated Wasm modules

## How It Works

1. The agent connects to `mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter`.
2. Wraps the specific MCP tools in custom `smolagents.Tool` subclasses.
3. Uses `ToolCallingAgent` equipped with LiteLLM (Anthropic) to evaluate and route requests.
4. When asked to extract posts, the agent intelligently calls the fetch tool first, receives a pointer, and then queries the remote JSON using the JQ tool, keeping its context window incredibly small.

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
   uv run python main.py
   ```
