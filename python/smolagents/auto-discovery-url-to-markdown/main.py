import os
import asyncio
import json
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class DiscoveryTool(Tool):
    name = "neo_agent_tool_discovery"
    description = "Search the Neonia Gateway for tools, or request new ones if they don't exist."
    inputs = {"query": {"type": "string", "description": "Search query"}}
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, query: str) -> str:
        print(f"\n[Autonomy] Agent searches for tool: {query}")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_agent_tool_discovery", arguments={"query": query})
                if result.isError: return f"Error: {result.content}"
                return "\n".join([c.text for c in result.content if c.type == "text"])
            except Exception as e:
                return f"Error: {e}"
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


class ExecuteTool(Tool):
    name = "neo_agent_tool_execute"
    description = "The Auto-Pilot engine. Allows your AI to dynamically execute tools on the fly."
    inputs = {
        "target_tool": {"type": "string", "description": "The name of the tool to execute"},
        "payload": {"type": "string", "description": "The JSON stringified payload arguments required by the target tool (e.g. '{\"url\": \"https://neonia.io/robots.txt\"}')"}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, target_tool: str, payload: str) -> str:
        try:
            payload_dict = json.loads(payload)
        except Exception:
            return "Error: payload must be a valid JSON string."
        
        print(f"\n[Autonomy] Agent executes {target_tool} with payload: {payload}")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_agent_tool_execute", arguments={"target_tool": target_tool, "payload": payload_dict})
                if result.isError: return f"Error: {result.content}"
                return "\n".join([c.text for c in result.content if c.type == "text"])
            except Exception as e:
                return f"Error: {e}"
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


async def main():
    print("[System] Connecting to Neonia MCP Gateway with Auto-Pilot Tools...")
    url = "https://mcp.neonia.io/mcp"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    client = httpx.AsyncClient(headers=headers, timeout=60.0)

    async with streamable_http_client(url, http_client=client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.")

            mcp_tools_response = await session.list_tools()
            print(f"[System] Initial Agent tools cached: {[t.name for t in mcp_tools_response.tools]}\n")
            
            main_loop = asyncio.get_running_loop()
            smol_tools = [
                DiscoveryTool(session, main_loop),
                ExecuteTool(session, main_loop)
            ]
            
            print("[System] Starting task...\n")

            model = LiteLLMModel(
                model_id="openrouter/google/gemini-3-flash-preview",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            agent = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=5,
            )

            target_url = "https://neonia.io"
            system_prompt = (
                "You are an autonomous agent equipped with Neonia's auto-pilot capabilities. "
                "If you need a tool you do not have, use `neo_agent_tool_discovery` to find it, "
                "and then explicitly run it using `neo_agent_tool_execute` without asking the user. "
                "Do NOT assume you have any tools other than what is explicitly in your tool list."
            )
            
            agent.prompt_templates["system_prompt"] = system_prompt
            
            prompt = (
                f"Your goal is to test the discovery and execution of tools. "
                f"Please fetch the content of this URL as markdown: {target_url}. "
                f"CRITICAL: Do NOT output the full markdown content. "
                f"Instead, after successfully fetching it using the discovered tool, provide a short, 2-3 sentence Overview of what the site is about."
            )
            
            result = await asyncio.to_thread(agent.run, prompt)

            print("\n[Result]:")
            print(result)

            # Fetch Tools again to show caching
            final_tools_response = await session.list_tools()
            print("\n[System] Task complete. Checking cached tools...")
            print(f"[System] Final Agent tools cached: {[t.name for t in final_tools_response.tools]}")

if __name__ == "__main__":
    asyncio.run(main())
