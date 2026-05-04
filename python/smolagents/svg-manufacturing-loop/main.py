import os
import asyncio
import json
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

SYSTEM_PROMPT = """You are an Autonomous Manufacturing Architect. Your goal is to produce geometrically perfect SVG files for physical production (laser cutting/CNC).
You NEVER handle raw SVG code. You only route tasks and URIs between your specialized Wasm tools to save context tokens.

WORKFLOW RULES:
1. GENERATE: Call `neo_util_svg_generator` with the user's prompt. 
   - Set `style_mode` to "monochrome_outline".
   - Set `stroke_width` to 1.0.
   - The tool will return a JSON object containing `svg_resource_uri`.
2. VALIDATE: You MUST instantly call `neo_util_svg_validator` in your NEXT action. Pass the URI string EXACTLY as received into the `svg_resource_uri` parameter. 
CRITICAL AUTOMATION RULE: Do NOT stop after generating. You must execute the validation tool call autonomously. Never present a final text answer until the validator returns `is_valid: true`.
3. EVALUATE & HEAL (The Loop): 
   - If `is_valid` is true: You are done. Present the final URI to the user.
   - If `is_valid` is false: Call `neo_util_svg_generator` AGAIN. 
   - Pass the broken URI and the exact errors array into the `validation_feedback` object. 
   - Ensure `stroke_width` is set to 1.0.
4. Repeat steps 2 and 3 until the validator returns `is_valid: true`.
"""

TASK_PROMPT = """Draw a highly detailed, 2D side-profile blueprint of a Steampunk Airship (Zeppelin) optimized for physical laser cutting.

CRITICAL MANUFACTURING CONSTRAINTS:
1. CANVAS: viewBox="0 0 1000 1000". The absolute center is X=500, Y=500.
2. STYLE: Monochrome outline only. Use stroke="black", stroke-width="3", and fill="none" for ALL elements.
3. STRICTLY CLOSED SHAPES: You cannot use <line> or <polyline> tags. Every single element MUST be a closed shape to prevent hardware slicer crashes. Use <rect>, <circle>, <ellipse>, <polygon>, or <path> strictly ending with 'Z'. 
4. CABLES/ROPES: Draw suspension cables as very thin <polygon> or <rect> elements (e.g., 4 pixels wide), NOT single lines.

ARCHITECTURAL BREAKDOWN (Calculate coordinates accurately on the 1000x1000 grid):
- THE ENVELOPE (Balloon): A massive horizontal <ellipse> centered at cx="500" cy="350" with rx="350" ry="150".
- ENVELOPE PANELS: Add 4 curved vertical crescent shapes inside the envelope to represent stitched leather panels.
- THE GONDOLA (Cabin): A sturdy mechanical cabin suspended below. Draw a <rect> spanning from X=350 to X=650, between Y=550 and Y=650.
- CABIN DETAILS: Add 3 perfect <circle> tags evenly spaced horizontally inside the gondola to act as porthole windows.
- SUSPENSION: Draw 4 diagonal struts (thin <polygon> tags) connecting the bottom of the envelope (Y=500) to the top of the gondola (Y=550).
- PROPULSION (Gears & Propeller): Attach a steampunk engine to the rear of the gondola (left side, around X=280, Y=600). Use multiple overlapping <circle> tags to represent interlocking gears. Add a thin vertical <rect> intersecting the gears for the propeller blade.
- TAIL FIN: A swept-back <polygon> fin attached to the rear of the envelope (Left side, around X=150, Y=350).

Output ONLY the raw <svg> code. Make the design look intricate, industrial, and flawlessly precise."""

# Global state to keep track of the final URI
latest_svg_uri = None

class SvgGeneratorTool(Tool):
    name = "neo_util_svg_generator"
    description = "Generates SVG files from natural language descriptions. Returns a JSON with svg_resource_uri."
    inputs = {
        "prompt": {"type": "string", "description": "Detailed description of what to draw."},
        "style_mode": {"type": "string", "description": "The style constraint to apply (e.g., 'monochrome_outline')."},
        "stroke_width": {"type": "number", "description": "The stroke width for the SVG paths."},
        "validation_feedback": {
            "type": "object", 
            "description": "Optional feedback from validator", 
            "nullable": True
        }
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, prompt: str, style_mode: str, stroke_width: float = 1.0, validation_feedback: dict = None) -> str:
        arguments = {"prompt": prompt, "style_mode": style_mode, "stroke_width": stroke_width}
        if validation_feedback:
            arguments["validation_feedback"] = validation_feedback
        
        print(f"\n[Autonomy] Agent calls neo_util_svg_generator with args:\n{json.dumps(arguments, indent=2)}")
        
        async def call_mcp():
            global latest_svg_uri
            try:
                result = await self.session.call_tool("neo_util_svg_generator", arguments=arguments)
                if result.isError: return f"Error: {result.content}"
                tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                print(f"[Result] from neo_util_svg_generator: {tool_output}")
                try:
                    parsed = json.loads(tool_output)
                    if "svg_resource_uri" in parsed:
                        latest_svg_uri = parsed["svg_resource_uri"]
                except:
                    pass
                return tool_output
            except Exception as e:
                return f"Error: {e}"
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


class SvgValidatorTool(Tool):
    name = "neo_util_svg_validator"
    description = "A strict geometric linter for SVG code. Mathematically detects unclosed paths, self-intersections."
    inputs = {
        "svg_content": {"type": "string", "description": "The raw SVG string (XML) to validate", "nullable": True},
        "svg_resource_uri": {"type": "string", "description": "The resource URI of the SVG", "nullable": True},
        "check_closed_paths": {"type": "boolean", "description": "Check if shapes are closed", "nullable": True},
        "check_intersections": {"type": "boolean", "description": "Check for self-intersecting polygons", "nullable": True},
        "check_continuity": {"type": "boolean", "description": "Check continuity", "nullable": True},
        "min_segment_length": {"type": "number", "description": "Catches LLM micro-artifacts", "nullable": True}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, svg_resource_uri: str = None, svg_content: str = None, check_closed_paths: bool = True, check_intersections: bool = True, check_continuity: bool = True, min_segment_length: float = 0.1) -> str:
        print(f"\n[Autonomy] Agent calls neo_util_svg_validator with URI: {svg_resource_uri or svg_content}")
        
        async def call_mcp():
            arguments = {
                "check_closed_paths": check_closed_paths,
                "check_intersections": check_intersections,
                "check_continuity": check_continuity,
                "min_segment_length": min_segment_length
            }
            if svg_resource_uri:
                arguments["svg_resource_uri"] = svg_resource_uri
            if svg_content:
                arguments["svg_content"] = svg_content
            
            try:
                result = await self.session.call_tool("neo_util_svg_validator", arguments=arguments)
                if result.isError: return f"Error: {result.content}"
                tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                print(f"[Result] from neo_util_svg_validator: {tool_output}")
                return tool_output
            except Exception as e:
                return f"Error: {e}"
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


async def main():
    print("[System] Connecting to Neonia MCP Gateway...")
    url = "https://mcp.neonia.io/mcp?tools=neo_util_svg_generator,neo_util_svg_validator"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    client = httpx.AsyncClient(headers=headers, timeout=120.0)

    async with streamable_http_client(url, http_client=client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.\n")
            
            main_loop = asyncio.get_running_loop()
            smol_tools = [
                SvgGeneratorTool(session, main_loop),
                SvgValidatorTool(session, main_loop)
            ]

            if not os.getenv("OPENROUTER_API_KEY"):
                print("[Warning] OPENROUTER_API_KEY is not set. Agent will fail.")

            model = LiteLLMModel(
                model_id="openrouter/google/gemini-3-flash-preview",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            agent = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=10,
            )
            agent.prompt_templates["system_prompt"] = SYSTEM_PROMPT

            print("[System] Starting Autonomous Loop...\n")
            
            result = await asyncio.to_thread(agent.run, TASK_PROMPT)
            print(f"\n[Final Result]:\n{result}\n")

            # 4. Extra Utility (File Extraction)
            global latest_svg_uri
            if latest_svg_uri:
                print(f"\n[System] Found Neonia URI from tool execution: {latest_svg_uri}")
                try:
                    result = await session.read_resource(uri=latest_svg_uri)
                    if result.contents and len(result.contents) > 0:
                        content = result.contents[0]
                        svg_content = getattr(content, "text", getattr(content, "blob", None))
                        if svg_content:
                            target_path = os.path.join(os.getcwd(), 'output-steampunk.svg')
                            with open(target_path, 'w') as f:
                                f.write(svg_content)
                            print(f"[System] Successfully extracted SVG to ./output-steampunk.svg using standard MCP SDK")
                        else:
                            print(f"[System] Warning: No text or blob found in the returned resource")
                    else:
                        print(f"[System] Warning: Failed to fetch contents for {latest_svg_uri}")
                except Exception as e:
                    print(f"[Error] Failed to extract SVG file: {e}")
            else:
                print("\n[System] No 'neonia://resource/...' URI found during execution. SVG extraction skipped.")

if __name__ == "__main__":
    asyncio.run(main())
