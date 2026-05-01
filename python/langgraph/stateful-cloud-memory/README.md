# Stateful Memory Note Example (Python / LangGraph)

This example demonstrates how to use the **Neonia System Memory Note** (`neo_sys_memory_note`) tool to create stateful agents that remember preferences, rules, or personas across entirely different sessions without needing complex RAG pipelines or databases.

## Scenario: The Imperial Droid 🌌

To showcase the power of dynamic memory, this script runs two distinct simulated sessions:

1. **Session 1 (Admin/Setup)**: The user commands the agent to adopt a new, strict persona (an Imperial Droid from Star Wars). The agent uses the `store` action of the Cloud Memory tool.
2. **Session 2 (New Day)**: A completely fresh LangGraph agent instance is created with **zero** local conversation history. The user simply asks for the weather on Hoth. The agent autonomously uses the `recall` action, retrieves the persona rules, and responds accordingly.

## Prerequisites

1. Create a `.env` file based on the example:

   ```bash
   cp .env.example .env
   ```

2. Add your [Neonia API Key](https://neonia.io/dashboard/api-keys) and your OpenRouter API key.
3. **IMPORTANT**: In your Neonia Dashboard, go to your Agent settings and ensure that **Cloud Memory** is toggled to **ON**.

## Setup & Run

1. Install dependencies using `uv`:

   ```bash
   uv sync
   ```

2. Run the agent:

   ```bash
   uv run python agent.py
   ```

## Expected Output

You should see the first agent successfully storing the persona context, and the second agent (which starts with a blank slate) fetching that context dynamically and responding in the correct character:
> *"My Lord, expect extreme blizzards and -60°C on Hoth tomorrow. Perfect weather to freeze out the Rebel terrorists. Long live the Empire!"*
