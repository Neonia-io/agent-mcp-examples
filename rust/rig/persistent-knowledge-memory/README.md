# Persistent Knowledge Memory Example (Rust / Rig)

This example demonstrates how to use the **Neonia Dual Memory Architecture** (`neo_sys_memory_lesson` for writing and `neo_sys_memory_search` for reading) to create agents that store and retrieve hard-learned architectural lessons (ADRs) across entirely different sessions without needing complex databases.

## Scenario: The Production Post-Mortem 🚨

To showcase the power of architectural memory, this script runs two distinct simulated sessions:

1. **Session 1 (Admin/Setup)**: The user informs the agent about a production crash caused by API context bloat. The agent uses the `neo_sys_memory_lesson` tool to securely store a strictly formatted rule (ADR) about using a jq filter.
2. **Session 2 (New Task)**: A completely fresh Rig agent instance is created with **zero** local conversation history. The user simply asks for the weather on Hoth. The agent autonomously uses the `neo_sys_memory_search` tool, retrieves the architectural rule about jq filters, and plans its approach accordingly.

## Prerequisites

1. Create a `.env` file based on the example:

   ```bash
   cp .env.example .env
   ```

2. Add your [Neonia API Key](https://neonia.io/dashboard/api-keys) and your OpenRouter API key.
3. **IMPORTANT**: In your Neonia Dashboard, go to your Agent settings and ensure that **Cloud Memory** is toggled to **ON**.

## Setup & Run

```bash
cargo run
```

## Expected Output

You should see the first agent successfully storing the structured architectural lesson, and the second agent (which starts with a blank slate) fetching that context dynamically and explicitly stating it will use a jq filter before parsing the API data.
