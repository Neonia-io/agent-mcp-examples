# Chained JSON JQ Filter Example (Rust / Rig)

This example demonstrates how to build an autonomous agent using **Rig** that avoids context window bloat by offloading data processing to a remote Wasm tool via the Neonia MCP Gateway.

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

## Architecture Notes

Rig provides native integration with the Model Context Protocol through the `rmcp_tools` method. 
The agent dynamically discovers the `neo_web_json_fetch` and `neo_data_jq_filter` tools from the gateway, allowing it to seamlessly construct the correct input payload for fetching the JSON and executing the JQ filter without loading any data locally.

## Setup

1. Configure your environment variables in `.env`:

   ```env
   OPENROUTER_API_KEY="your-openrouter-key"
   NEONIA_API_KEY="your-neonia-key"
   ```

2. Run the application:

   ```bash
   cargo run
   ```
