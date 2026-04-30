import os
import asyncio
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import httpx

load_dotenv()

async def main():
    print("[System] Connecting to Neonia MCP Gateway...")
    url = "https://mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter"
    
    # 1. Setup MCP Client via SSE
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    async with streamable_http_client(url, http_client=httpx.AsyncClient(headers=headers, timeout=60.0)) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.")

            # 2. Fetch available tools from the MCP server
            mcp_tools_response = await session.list_tools()
            allowed_tools = ["neo_web_json_fetch", "neo_data_jq_filter"]
            filtered_mcp_tools = [t for t in mcp_tools_response.tools if t.name in allowed_tools]
            
            # 3. Create LangChain tools wrapping MCP tool execution
            langchain_tools = []
            
            for mcp_tool in filtered_mcp_tools:
                if mcp_tool.name == "neo_web_json_fetch":
                    def create_fetch_wrapper(mcp_name: str, mcp_desc: str):
                        async def neo_web_json_fetch(url: str) -> str:
                            kwargs = {"url": url}
                            print(f"\n[Autonomy] Agent calls {mcp_name} with arguments: {json.dumps(kwargs)}")
                            try:
                                result = await session.call_tool(mcp_name, arguments=kwargs)
                                if result.isError: return f"Error: {result.content}"
                                return "\n".join([c.text for c in result.content if c.type == "text"])
                            except Exception as e:
                                return f"Error: {e}"
                        neo_web_json_fetch.__name__ = mcp_name
                        neo_web_json_fetch.__doc__ = mcp_desc
                        return tool()(neo_web_json_fetch)
                    langchain_tools.append(create_fetch_wrapper(mcp_tool.name, mcp_tool.description))
                elif mcp_tool.name == "neo_data_jq_filter":
                    def create_jq_wrapper(mcp_name: str, mcp_desc: str):
                        async def neo_data_jq_filter(jq_query: str, data_url: str = None, raw_json: str = None, resource_uri: str = None) -> str:
                            kwargs = {"jq_query": jq_query}
                            if data_url is not None: kwargs["data_url"] = data_url
                            if raw_json is not None: kwargs["raw_json"] = raw_json
                            if resource_uri is not None: kwargs["resource_uri"] = resource_uri
                            print(f"\n[Autonomy] Agent calls {mcp_name} with arguments: {json.dumps(kwargs)}")
                            try:
                                result = await session.call_tool(mcp_name, arguments=kwargs)
                                if result.isError: return f"Error: {result.content}"
                                return "\n".join([c.text for c in result.content if c.type == "text"])
                            except Exception as e:
                                return f"Error: {e}"
                        neo_data_jq_filter.__name__ = mcp_name
                        neo_data_jq_filter.__doc__ = mcp_desc
                        return tool()(neo_data_jq_filter)
                    langchain_tools.append(create_jq_wrapper(mcp_tool.name, mcp_tool.description))
            
            print(f"[System] Agent equipped with {len(langchain_tools)} foundational tools.")
            print("[System] Starting task...\n")

            # 4. Run Agent via LangGraph
            model = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="anthropic/claude-3.7-sonnet"
            )
            agent_executor = create_agent(model, langchain_tools)

            target_url = "https://dummyjson.com/posts"
            
            system_prompt = SystemMessage(content=(
                "You are an autonomous agent equipped with Neonia's data processing tools.\n"
                "## Usage Guidelines\n"
                "1. When asked to process JSON from a URL, ALWAYS use `neo_web_json_fetch` first. It will securely store the file and return a `resource_uri` and a TypeScript schema of the data.\n"
                "2. Once you have the `resource_uri` and the schema, use `neo_data_jq_filter` to extract exactly what you need. Pass the `resource_uri` to the `resource_uri` parameter, and formulate a mathematically precise `jq_query` based on the schema.\n"
                "3. Write correct JQ queries. If the JSON has a wrapper object like `.posts`, use appropriate mapping. Example: `.posts[0:10] | map({title: .title, body: .body})`.\n"
                "4. Self-Correction: If a tool returns an error, evaluate your parameters, fix them, and try again."
            ))
            user_prompt = f"Fetch the JSON from {target_url}, then use the jq filter to extract the title and body of the first 10 posts. Finally, provide a brief summary of the posts."
            
            messages = [system_prompt, {"role": "user", "content": user_prompt}]
            
            async for event in agent_executor.astream_events({"messages": messages}, version="v1"):
                kind = event["event"]
                if kind == "on_tool_start":
                    print(f"[Autonomy] Agent called tool: {event['name']}")
                elif kind == "on_tool_end":
                    if event["name"] == "neo_web_json_fetch":
                        print("[Autonomy] Fetched JSON successfully and received pointer!")
                    elif event["name"] == "neo_data_jq_filter":
                        print("[Autonomy] Filtered JSON successfully using JQ and pointer!")

            final_state = await agent_executor.ainvoke({"messages": messages})
            print("\n[Result]:")
            print(final_state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
