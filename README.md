# Stop Vibe Coding. Start Engineering. 🚀

**Examples of autonomous AI agents using the Model Context Protocol (MCP) and Neonia.**

These examples demonstrate how to build deterministic, high-performance AI agents. By utilizing **[Neonia](https://neonia.io)** as a Wasm-powered MCP Gateway, agents can offload heavy processing to specialized tools, avoiding token bloat and executing with near-zero latency.

## Ecosystem Architecture

Our examples are categorized by language and framework to help you find the exact pattern you need.

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
  _Demonstrates how an autonomous agent can use tool discovery and a Wasm-powered JQ filter to extract specific data from large JSON payloads. Instead of loading massive JSONs directly into the LLM context, it executes JQ tools remotely, saving up to 50,000+ tokens per request._

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
   *(Note: The Neonia Gateway requires a free API key to authenticate MCP connections).*

4. Install dependencies and run:
   ```bash
   npm install
   npx tsx index.ts
   ```
