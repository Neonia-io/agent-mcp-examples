import os
import asyncio
import json
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class FetchTool(Tool):
    def __init__(self, name: str, description: str, session: ClientSession, loop: asyncio.AbstractEventLoop):
        self.name = name
        self.description = description
        self.session = session
        self.loop = loop
        self.inputs = {"url": {"type": "string", "description": "URL to fetch JSON from"}}
        self.output_type = "string"
        self.is_initialized = True

    def forward(self, url: str) -> str:
        kwargs = {"url": url}
        print(f"\n[Autonomy] Agent calls {self.name} with arguments: {json.dumps(kwargs)}")
        async def call_mcp():
            try:
                result = await self.session.call_tool(self.name, arguments=kwargs)
                if result.isError: return f"Error: {result.content}"
                return "\n".join([c.text for c in result.content if c.type == "text"])
            except Exception as e:
                return f"Error: {e}"
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()

class JQFilterTool(Tool):
    def __init__(self, name: str, description: str, session: ClientSession, loop: asyncio.AbstractEventLoop):
        self.name = name
        self.description = description
        self.session = session
        self.loop = loop
        self.inputs = {"data_url": {"type": "string", "description": "URL to fetch JSON from", "nullable": True},
                       "jq_query": {"type": "string", "description": "JQ query to execute"},
                       "raw_json": {"type": "string", "description": "Raw JSON string", "nullable": True},
                       "resource_uri": {"type": "string", "description": "Resource URI pointer", "nullable": True}}
        self.output_type = "string"
        self.is_initialized = True

    def forward(self, jq_query: str, data_url: str = None, raw_json: str = None, resource_uri: str = None) -> str:
        kwargs = {"jq_query": jq_query}
        if data_url is not None: kwargs["data_url"] = data_url
        if raw_json is not None: kwargs["raw_json"] = raw_json
        if resource_uri is not None: kwargs["resource_uri"] = resource_uri
        
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
    url = "https://mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    async with streamable_http_client(url, http_client=httpx.AsyncClient(headers=headers, timeout=60.0)) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.")

            mcp_tools_response = await session.list_tools()
            allowed_tools = ["neo_web_json_fetch", "neo_data_jq_filter"]
            filtered_mcp_tools = [t for t in mcp_tools_response.tools if t.name in allowed_tools]
            
            main_loop = asyncio.get_running_loop()
            
            smol_tools = []
            for mcp_tool in filtered_mcp_tools:
                if mcp_tool.name == "neo_web_json_fetch":
                    smol_tools.append(FetchTool(mcp_tool.name, mcp_tool.description, session, main_loop))
                elif mcp_tool.name == "neo_data_jq_filter":
                    smol_tools.append(JQFilterTool(mcp_tool.name, mcp_tool.description, session, main_loop))
            
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

            target_url = "https://dummyjson.com/posts"
            system_prompt = (
                "You are an autonomous agent equipped with Neonia's data processing tools.\n"
                "## Usage Guidelines\n"
                "1. When asked to process JSON from a URL, ALWAYS use `neo_web_json_fetch` first. It will securely store the file and return a `resource_uri` and a TypeScript schema of the data.\n"
                "2. Once you have the `resource_uri` and the schema, use `neo_data_jq_filter` to extract exactly what you need. Pass the `resource_uri` to the `resource_uri` parameter, and formulate a mathematically precise `jq_query` based on the schema.\n"
                "3. Write correct JQ queries. If the JSON has a wrapper object like `.posts`, use appropriate mapping. Example: `.posts[0:10] | map({title: .title, body: .body})`.\n"
                "4. Self-Correction: If a tool returns an error, evaluate your parameters, fix them, and try again."
            )
            
            agent.prompt_templates["system_prompt"] = system_prompt
            
            prompt = f"Fetch the JSON from {target_url}, then use the jq filter to extract the title and body of the first 10 posts. Finally, provide a brief summary of the posts."
            result = await asyncio.to_thread(agent.run, prompt)

            print("\n[Result]:")
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
