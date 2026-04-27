# Auto-Pilot Tool Discovery Example (Rust)

This example demonstrates how to build a fully autonomous agent using the **Rig** agent framework that dynamically discovers and executes missing capabilities on the fly via the Neonia MCP Gateway.

## The Problem: Tool Rigidity

Traditionally, AI agents are hard-coded with a static list of tools. If a user asks for something outside that predefined list (like scraping a URL or checking a stock price), the framework lacks the capability. This approach:

1. Forces developers to predict every possible user request.
2. Bloats the system prompt with hundreds of tool schemas.
3. Often leads to the agent hallucinating or failing when an unknown request is encountered.

## The Neonia Solution: Auto-Pilot Discovery

Instead of pre-loading tools, this agent is equipped with only two meta-tools from the Neonia MCP Gateway:
- `neo_agent_tool_discovery`: Searches the global Neonia registry for missing capabilities.
- `neo_agent_tool_execute`: Dynamically executes the discovered tool using its required JSON payload.

When asked to summarize the `neonia.io` webpage, the agent realizes it lacks a web scraping tool. It autonomously searches the Gateway, discovers the `neo_web_url_to_markdown` tool, and executes it perfectly without any human intervention or code changes.

### Impact

- **Infinite Capabilities:** The agent has access to the entire Neonia library on demand.
- **Prompt Optimization:** Only the active tools consume context tokens.
- **True Autonomy:** The agent learns and adapts to user requests in real-time.

## How It Works

1. The agent connects to `mcp.neonia.io/mcp?tools=neo_agent_tool_discovery,neo_agent_tool_execute`.
2. It dynamically maps these MCP meta-tools into Rig's statically-typed tool structure.
3. Rig builds an agent equipped with these capabilities, connecting to the underlying LLM via OpenRouter.
4. When asked to fetch a URL, the agent searches for a tool, finds `neo_web_url_to_markdown`, and immediately executes it.

## Setup

1. Create a `.env` file with your API keys:

   ```env
   OPENROUTER_API_KEY="your-openrouter-key"
   NEONIA_API_KEY="your-neonia-key"
   ```

2. Run the agent:

   ```bash
   cargo run
   ```
