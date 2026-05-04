# SVG Manufacturing Loop Example (Vercel AI SDK)

This example demonstrates a "Closed-Loop Generative-Adversarial Workflow" using Neonia's Pass-by-Reference architecture and the **Vercel AI SDK**.

## The Problem: Token Bloat & Code Breakage

When generating large vector files like SVGs (especially those meant for physical production like laser cutting or CNC), handling the raw XML code inside an LLM's context window leads to:
1. Massive token consumption (bloat).
2. Code truncation or malformed tags due to output limits.
3. Errors in physical manufacturing (e.g. self-intersecting polygons) that standard LLMs cannot inherently "see" without geometric rendering.

## The Neonia Solution: Token Arbitrage & Autonomous Healing

This agent operates as a "Manufacturing Architect". It doesn't write SVG code itself. Instead, it delegates tasks to specialized Neonia Wasm tools running on the Gateway, communicating entirely via lightweight URIs (`neo://`). 

The architecture is known as **Token Arbitrage**: trading heavy text generation for lightweight API coordination, thus shifting the compute burden to specific, optimized tools and saving massive context space.

### The Loop:
1. **Generate**: The orchestrator asks `neo_util_svg_generator` to create an SVG. It receives back a URI (e.g. `neo://tmp/xwing.svg`). The LLM never sees the 500+ lines of SVG.
2. **Validate**: The orchestrator instantly passes this URI to `neo_util_svg_validator`, a strict geometric linter.
3. **Heal**: If errors are found, the orchestrator loops back. It passes the broken URI and the error coordinates back into the generator, dynamically switching to a heavier, math-focused model to heal the file.
4. **Finalize**: Once validation passes, the agent presents the URI to the user, and our local script extracts it to an easily viewable `output-xwing.svg` file.

## How to Run

Ensure you have set the `NEONIA_API_KEY` and `OPENROUTER_API_KEY` in your `.env` file.

```bash
npm install
npm start
```

Watch the terminal as the agent generates, validates, and potentially heals the SVG autonomously, acting as a real-world manufacturing AI!
