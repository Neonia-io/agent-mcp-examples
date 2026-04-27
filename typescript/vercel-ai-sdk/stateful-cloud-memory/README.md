# Stateful Cloud Memory Example (TypeScript / Vercel AI SDK)

This example demonstrates how to use the **Neonia Cloud Memory** (`neo_agent_cloud_memory`) tool to create stateful agents that remember preferences, rules, or personas across entirely different sessions without needing complex RAG pipelines or databases.

## Scenario: The Imperial Droid 🌌
To showcase the power of dynamic memory, this script runs two distinct simulated sessions:
1. **Session 1 (Admin/Setup)**: The user commands the agent to adopt a new, strict persona (an Imperial Droid from Star Wars). The agent uses the `store` action of the Cloud Memory tool.
2. **Session 2 (New Day)**: A completely fresh Vercel AI SDK agent instance is created with **zero** local conversation history. The user simply asks for the weather on Hoth. The agent autonomously uses the `recall` action, retrieves the persona rules, and responds accordingly.

## Prerequisites

1. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```
2. Add your [Neonia API Key](https://neonia.io/dashboard/api-keys) and your OpenRouter API key.
3. **IMPORTANT**: In your Neonia Dashboard, go to your Agent settings and ensure that **Cloud Memory** is toggled to **ON**.

## Setup & Run

```bash
# Install dependencies
npm install

# Run the agent
npm start
```

## Expected Output
You should see the first agent successfully storing the persona context, and the second agent (which starts with a blank slate) fetching that context dynamically and responding in the correct character:
> *"My Lord, expect extreme blizzards and -60°C on Hoth tomorrow. Perfect weather to freeze out the Rebel terrorists. Long live the Empire!"*
