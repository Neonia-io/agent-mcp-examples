# Zero-Bloat JQ Filter Example (Rust / Rig)

This example demonstrates how to build an autonomous agent using **Rig** that avoids context window bloat by offloading data processing to a remote Wasm tool via the Neonia MCP Gateway.

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

## Architecture Notes

Rig strongly enforces statically typed tools defined as Rust structs implementing the `Tool` trait. Because MCP tools are dynamically discovered via JSON Schema at runtime, a fully dynamic LangChain-style integration requires custom dynamic dispatch.
This implementation demonstrates the structural pattern of bridging an initialized `rust-mcp-sdk` connection to a Rig agent conceptually.

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
