# Neonia Agent MCP Examples

A collection of autonomous agent examples demonstrating how to integrate the **Neonia Model Context Protocol (MCP) Gateway** using the official **Streamable HTTP** transport standard.

## About These Examples

This repository will continuously grow with new patterns demonstrating deterministic, high-performance AI agents.

Our first major showcase focuses on solving a critical problem in modern agent architectures: **Context Window Bloat**.

Traditionally, when an agent needs to extract data from a large 5MB JSON file, it loads the entire file into its context window, causing massive token consumption, high latency, and LLM "amnesia".

By connecting to the Neonia MCP Gateway (`mcp.neonia.io/mcp?tools=neo_data_jq_filter`), our `zero-bloat-jq-filter` agents explicitly bind the **Wasm-powered JQ Filter** tool. The agent executes queries on the remote server and receives only the filtered result (e.g. `$651,758.23`), saving **~50,000+ tokens** per request and responding almost instantly.

_(More examples covering vision extraction, dynamic execution, and multi-agent orchestration will be added soon!)_

## Examples Provided

This repository includes the "Zero-Bloat JQ Filter" implementation across 4 major agentic frameworks in 3 different languages:

### 1. Python (LangGraph)

A deterministic workflow using **LangChain** and **LangGraph** to build a reactive agent (`create_agent`) that dynamically wraps MCP capabilities into native LangChain `@tool` instances.

- **Directory**: `python/langgraph/zero-bloat-jq-filter`
- **Setup**: `uv sync && uv run python agent.py`

### 2. Python (SmolAgents)

A self-assembling agent using Hugging Face's **SmolAgents** and **LiteLLM**. Demonstrates subclassing `smolagents.Tool` for synchronous forward execution wrapped around an asynchronous Streamable HTTP session.

- **Directory**: `python/smolagents/zero-bloat-jq-filter`
- **Setup**: `uv sync && uv run python main.py`

### 3. TypeScript (Vercel AI SDK)

An integration with the **Vercel AI SDK** utilizing the official `@modelcontextprotocol/sdk` and `@openrouter/ai-sdk-provider`. Demonstrates proper multi-turn tool calling and schema mapping for Claude 3.7 Sonnet.

- **Directory**: `typescript/vercel-ai-sdk/zero-bloat-jq-filter`
- **Setup**: `npm install && npm start`

### 4. Rust (Rig)

A statically-typed integration using the **Rig** agent framework and `rust-mcp-sdk`. Demonstrates bridging an initialized MCP client session into Rust's strong type system.

- **Directory**: `rust/rig/zero-bloat-jq-filter`
- **Setup**: `cargo run`

## Prerequisites

To run these examples, you will need:

1. A **Neonia API Key** (`NEONIA_API_KEY`)
2. An **OpenRouter API Key** (`OPENROUTER_API_KEY`)

Configure these in the `.env` file within the specific example directory you wish to run.

## Ecosystem Architecture

```text
agent-mcp-examples/
├── typescript/                 # TypeScript Ecosystem
│   └── vercel-ai-sdk/          # Vercel AI SDK Framework
│       └── zero-bloat-jq-filter/   # Agentic Data Processing
│
├── python/                     # Python Ecosystem
│   ├── langgraph/              # LangGraph Framework
│   │   └── zero-bloat-jq-filter/
│   └── smolagents/             # SmolAgents Framework
│       └── zero-bloat-jq-filter/
│
└── rust/                       # Rust Ecosystem
    └── rig/                    # Rig Framework
        └── zero-bloat-jq-filter/
```

## Available Examples

Each example is self-contained and demonstrates the "Zero-Bloat" architectural pattern using the JQ filter tool over MCP.

- 📂 **[zero-bloat-jq-filter](./typescript/vercel-ai-sdk/zero-bloat-jq-filter/) (TypeScript / Vercel AI SDK)**
- 📂 **[zero-bloat-jq-filter](./python/langgraph/zero-bloat-jq-filter/) (Python / LangGraph)**
- 📂 **[zero-bloat-jq-filter](./python/smolagents/zero-bloat-jq-filter/) (Python / SmolAgents)**
- 📂 **[zero-bloat-jq-filter](./rust/rig/zero-bloat-jq-filter/) (Rust / Rig)**

## Getting Started

To run the examples, you will need an Anthropic API key (for the AI agent) and a free Neonia API key (for the Wasm MCP Gateway).

1. Clone the repository:

   ```bash
   git clone https://github.com/neonia-io/agent-mcp-examples.git
   cd agent-mcp-examples
   ```

2. Navigate to the example you want to try:

   ```bash
   cd typescript/vercel-ai-sdk/zero-bloat-jq-filter
   ```

3. Set up environment variables:

   ```env
   OPENROUTER_API_KEY="your-openrouter-key"
   NEONIA_API_KEY="your-neonia-key"
   ```

   _(Note: The Neonia Gateway requires a free API key to authenticate MCP connections)._

4. Install dependencies and run:

   ```bash
   npm install
   npx tsx index.ts
   ```
