# SVG Manufacturing Loop (smolagents)

This example demonstrates the Autonomous Manufacturing Loop using the Neonia Pass-by-Reference architecture.
It uses two Wasm Component tools via the Neonia MCP Gateway: `neo_util_svg_generator` and `neo_util_svg_validator`.

The autonomous agent is instructed to generate an SVG, strictly validate it for mathematical closure, and recursively self-heal if the validator finds any unclosed paths or self-intersections.

## Setup
1. Copy `.env.example` to `.env` and fill in your keys.
2. Run using uv: `uv run main.py`
