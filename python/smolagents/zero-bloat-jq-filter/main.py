import os
import asyncio
import json
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class MCPToolWrapper(Tool):
    def __init__(self, name: str, description: str, session: ClientSession, loop: asyncio.AbstractEventLoop):
        self.name = name
        self.description = description
        self.session = session
        self.loop = loop
        self.inputs = {"data_url": {"type": "string", "description": "URL to fetch JSON from", "nullable": True},
                       "jq_query": {"type": "string", "description": "JQ query to execute"},
                       "raw_json": {"type": "string", "description": "Raw JSON string", "nullable": True}}
        self.output_type = "string"
        self.is_initialized = True

    def forward(self, jq_query: str, data_url: str = None, raw_json: str = None) -> str:
        kwargs = {"jq_query": jq_query}
        if data_url is not None: kwargs["data_url"] = data_url
        if raw_json is not None: kwargs["raw_json"] = raw_json
        
        print(f"\n[Autonomy] Agent calls {self.name} with arguments: {json.dumps(kwargs)}")
        
        async def call_mcp():
            try:
                result = await self.session.call_tool(self.name, arguments=kwargs)
                if result.isError:
                    return f"Error: {result.content}"
                return "\n".join([c.text for c in result.content if c.type == "text"])
            except Exception as e:
                print(f"[Error] Execution error in {self.name}: {e}")
                return f"Error: {e}"
        
        # smolagents Tool.forward is sync, so we schedule the coroutine in the main loop
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


async def main():
    print("[System] Connecting to Neonia MCP Gateway...")
    url = "https://mcp.neonia.io/mcp?tools=neo_data_jq_filter"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    async with streamable_http_client(url, http_client=httpx.AsyncClient(headers=headers, timeout=60.0)) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.")

            mcp_tools_response = await session.list_tools()
            allowed_tools = ["neo_data_jq_filter"]
            filtered_mcp_tools = [t for t in mcp_tools_response.tools if t.name in allowed_tools]
            
            main_loop = asyncio.get_running_loop()
            
            smol_tools = []
            for mcp_tool in filtered_mcp_tools:
                smol_tools.append(MCPToolWrapper(mcp_tool.name, mcp_tool.description, session, main_loop))
            
            print(f"[System] Agent equipped with {len(smol_tools)} foundational tools.")
            print("[System] Starting task...\n")

            model = LiteLLMModel(
                model_id="openrouter/anthropic/claude-3.7-sonnet",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            agent = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=5,
            )

            target_url = "https://dummyjson.com/carts"
            system_prompt = (
                "You are an autonomous agent equipped with the neo_data_jq_filter tool.\n"
                "CRITICAL SYSTEM TOOL: This is a core data manipulation capability. ALWAYS use this to extract specific fields or filter arrays from large JSON files instead of trying to parse them entirely inside your context window or hallucinating data structures.\n"
                "## Usage Guidelines\n"
                "1. Prefer data_url for large files: If you need to read JSON from a URL (e.g. an API endpoint), pass the URL to data_url and the tool will fetch and process it natively in its memory, completely bypassing your token limits.\n"
                "2. Use raw_json for existing data: If you already have the data in a variable or context and just need to query it, pass it as a string to raw_json.\n"
                "3. Write correct JQ queries: Pass the filter to jq_query. Examples: .[] | .id, .users[0].name, map(select(.active == true)).\n"
                "4. Self-Correction: If the tool returns 'Invalid JQ syntax. Please correct your query.', evaluate your query string, fix the syntax error, and call the tool again."
            )
            
            agent.prompt_templates["system_prompt"] = system_prompt
            
            prompt = f"Find the total discountedTotal for all carts at this URL: {target_url}"
            result = await asyncio.to_thread(agent.run, prompt)

            print("\n[Result]:")
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
