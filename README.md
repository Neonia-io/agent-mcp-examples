# Neonia Agent MCP Examples

A collection of autonomous agent examples demonstrating how to integrate the **Neonia Model Context Protocol (MCP) Gateway** using the official **Streamable HTTP** transport standard.

## About These Examples

This repository will continuously grow with new patterns demonstrating deterministic, high-performance AI agents.

Our first major showcases focus on solving two critical problems in modern agent architectures: **Context Window Bloat** and **Tool Rigidity**.

#### 1. Solving Tool Rigidity (Auto-Pilot Discovery)

Agents are traditionally hard-coded with a static list of tools. If a user asks for something outside that list, the agent hallucinates or fails. The `auto-discovery-url-to-markdown` examples demonstrate how to give your agents true autonomy. By connecting to the Neonia Gateway, the agent can dynamically search for missing capabilities, read the tool's schema, and execute it on the fly without human intervention.

#### 2. Solving Context Bloat (Zero-Bloat Data Processing)

Traditionally, when an agent needs to extract data from a large 5MB JSON file, it loads the entire file into its context window, causing massive token consumption, high latency, and LLM "amnesia". By connecting to the Neonia MCP Gateway (`mcp.neonia.io/mcp?tools=neo_data_jq_filter`), our `zero-bloat-jq-filter` agents explicitly bind the **Wasm-powered JQ Filter** tool. The agent executes queries on the remote server and receives only the filtered result (e.g. `$651,758.23`), saving **~50,000+ tokens** per request and responding almost instantly.

#### 3. Stateful Cloud Memory (`stateful-cloud-memory`)

Agents typically suffer from absolute amnesia between sessions. If a user states a preference or business rule, it is lost unless hardcoded into the system prompt. The `stateful-cloud-memory` examples demonstrate how to create stateful agents that use Neonia's Cloud Memory to dynamically store and recall rules (like custom personas or user preferences) across completely isolated sessions without needing a custom database.

_(More examples covering vision extraction, dynamic execution, and multi-agent orchestration will be added soon!)_

## Examples Provided

This repository includes implementations of "Zero-Bloat Data Processing", "Auto-Pilot Tool Discovery", and "Stateful Cloud Memory" across major agentic frameworks in 3 different languages:

### 1. Python (LangGraph)

A deterministic workflow using **LangChain** and **LangGraph** to build a reactive agent (`create_agent`) that dynamically wraps MCP capabilities into native LangChain `@tool` instances.

- **Directories**: `python/langgraph/zero-bloat-jq-filter`, `python/langgraph/auto-discovery-url-to-markdown`, `python/langgraph/stateful-cloud-memory`
- **Setup**: `uv sync && uv run python agent.py`

### 2. Python (SmolAgents)

A self-assembling agent using Hugging Face's **SmolAgents** and **LiteLLM**. Demonstrates subclassing `smolagents.Tool` for synchronous forward execution wrapped around an asynchronous Streamable HTTP session.

- **Directories**: `python/smolagents/zero-bloat-jq-filter`, `python/smolagents/auto-discovery-url-to-markdown`
- **Setup**: `uv sync && uv run python main.py`

### 3. TypeScript (Vercel AI SDK)

An integration with the **Vercel AI SDK** utilizing the official `@modelcontextprotocol/sdk` and `@openrouter/ai-sdk-provider`. Demonstrates proper multi-turn tool calling and schema mapping for Claude 3.7 Sonnet.

- **Directories**: `typescript/vercel-ai-sdk/zero-bloat-jq-filter`, `typescript/vercel-ai-sdk/auto-discovery-url-to-markdown`, `typescript/vercel-ai-sdk/stateful-cloud-memory`
- **Setup**: `npm install && npm start`

### 4. Rust (Rig)

A statically-typed integration using the **Rig** agent framework and `rust-mcp-sdk`. Demonstrates bridging an initialized MCP client session into Rust's strong type system.

- **Directories**: `rust/rig/zero-bloat-jq-filter`, `rust/rig/auto-discovery-url-to-markdown`, `rust/rig/stateful-cloud-memory`
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
│       ├── zero-bloat-jq-filter/           # Agentic Data Processing
│       ├── auto-discovery-url-to-markdown/ # Auto-Pilot Tool Discovery
│       └── stateful-cloud-memory/          # Cloud Memory Persistence
│
├── python/                     # Python Ecosystem
│   ├── langgraph/              # LangGraph Framework
│   │   ├── zero-bloat-jq-filter/
│   │   ├── auto-discovery-url-to-markdown/
│   │   └── stateful-cloud-memory/
│   └── smolagents/             # SmolAgents Framework
│       ├── zero-bloat-jq-filter/
│       ├── auto-discovery-url-to-markdown/
│       └── stateful-cloud-memory/
│
└── rust/                       # Rust Ecosystem
    └── rig/                    # Rig Framework
        ├── zero-bloat-jq-filter/
        ├── auto-discovery-url-to-markdown/
        └── stateful-cloud-memory/
```

## Available Examples

Each example is self-contained and demonstrates specific, production-ready architectural patterns over MCP.

### 1. Auto-Pilot Tool Discovery (`auto-discovery-url-to-markdown`)

Demonstrates how to give agents true autonomy. If an agent lacks a required capability, it dynamically searches the Neonia Gateway for a matching tool, reads its parameters, and executes it on the fly without human intervention.

- 📂 **[auto-discovery-url-to-markdown](./typescript/vercel-ai-sdk/auto-discovery-url-to-markdown/) (TypeScript / Vercel AI SDK)**
- 📂 **[auto-discovery-url-to-markdown](./python/langgraph/auto-discovery-url-to-markdown/) (Python / LangGraph)**
- 📂 **[auto-discovery-url-to-markdown](./python/smolagents/auto-discovery-url-to-markdown/) (Python / SmolAgents)**
- 📂 **[auto-discovery-url-to-markdown](./rust/rig/auto-discovery-url-to-markdown/) (Rust / Rig)**

### 2. Zero-Bloat Data Processing (`zero-bloat-jq-filter`)

Demonstrates how to safely process massive API payloads using a deterministic Wasm JQ filter at the edge, drastically reducing LLM token context usage and preventing hallucination.

- 📂 **[zero-bloat-jq-filter](./typescript/vercel-ai-sdk/zero-bloat-jq-filter/) (TypeScript / Vercel AI SDK)**
- 📂 **[zero-bloat-jq-filter](./python/langgraph/zero-bloat-jq-filter/) (Python / LangGraph)**
- 📂 **[zero-bloat-jq-filter](./python/smolagents/zero-bloat-jq-filter/) (Python / SmolAgents)**
- 📂 **[zero-bloat-jq-filter](./rust/rig/zero-bloat-jq-filter/) (Rust / Rig)**

### 3. Stateful Cloud Memory (`stateful-cloud-memory`)

Demonstrates how to use the Cloud Memory tool (`neo_sys_memory_note`) to allow an agent to remember personas or business rules across completely isolated sessions.

- 📂 **[stateful-cloud-memory](./typescript/vercel-ai-sdk/stateful-cloud-memory/) (TypeScript / Vercel AI SDK)**
- 📂 **[stateful-cloud-memory](./python/langgraph/stateful-cloud-memory/) (Python / LangGraph)**
- 📂 **[stateful-cloud-memory](./python/smolagents/stateful-cloud-memory/) (Python / SmolAgents)**
- 📂 **[stateful-cloud-memory](./rust/rig/stateful-cloud-memory/) (Rust / Rig)**

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
