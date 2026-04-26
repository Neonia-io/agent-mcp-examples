# Zero-Bloat JQ Filter Example (Vercel AI SDK)

This example demonstrates how to build an autonomous agent using the **Vercel AI SDK** that avoids context window bloat by offloading data processing to a remote Wasm tool via the Neonia MCP Gateway.

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

## How to Run

Ensure you have set the `NEONIA_API_KEY` and `OPENROUTER_API_KEY` in your `.env` file.

```bash
npm install
npm start
```
