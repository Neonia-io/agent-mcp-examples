import os
import asyncio
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import httpx

load_dotenv()

async def main():
    print("[System] Connecting to Neonia MCP Gateway...")
    url = "https://mcp.neonia.io/mcp?tools=neo_data_jq_filter"
    
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
            allowed_tools = ["neo_data_jq_filter"]
            filtered_mcp_tools = [t for t in mcp_tools_response.tools if t.name in allowed_tools]
            
            # 3. Create LangChain tools wrapping MCP tool execution
            langchain_tools = []
            
            for mcp_tool in filtered_mcp_tools:
                def create_wrapper(mcp_name: str, mcp_desc: str):
                    async def mcp_tool_wrapper(jq_query: str, data_url: str = None, raw_json: str = None) -> str:
                        kwargs = {"jq_query": jq_query}
                        if data_url is not None: kwargs["data_url"] = data_url
                        if raw_json is not None: kwargs["raw_json"] = raw_json
                        print(f"\n[Autonomy] Agent calls {mcp_name} with arguments: {json.dumps(kwargs)}")
                        try:
                            result = await session.call_tool(mcp_name, arguments=kwargs)
                            
                            if result.isError:
                                return f"Error: {result.content}"
                                
                            text_parts = [c.text for c in result.content if c.type == "text"]
                            return "\n".join(text_parts)
                        except Exception as e:
                            print(f"[Error] Execution error in {mcp_name}: {e}")
                            return f"Error: {e}"
                    
                    mcp_tool_wrapper.__name__ = mcp_name
                    mcp_tool_wrapper.__doc__ = mcp_desc
                    return tool()(mcp_tool_wrapper)
                
                langchain_tools.append(create_wrapper(mcp_tool.name, mcp_tool.description))
            
            print(f"[System] Agent equipped with {len(langchain_tools)} foundational tools.")
            print("[System] Starting task...\n")

            # 4. Run Agent via LangGraph
            model = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="anthropic/claude-3.7-sonnet"
            )
            agent_executor = create_react_agent(model, langchain_tools)

            target_url = "https://dummyjson.com/carts"
            
            system_prompt = SystemMessage(content=(
                "You are an autonomous agent equipped with the neo_data_jq_filter tool.\n"
                "CRITICAL SYSTEM TOOL: This is a core data manipulation capability. ALWAYS use this to extract specific fields or filter arrays from large JSON files instead of trying to parse them entirely inside your context window or hallucinating data structures.\n"
                "## Usage Guidelines\n"
                "1. Prefer data_url for large files: If you need to read JSON from a URL (e.g. an API endpoint), pass the URL to data_url and the tool will fetch and process it natively in its memory, completely bypassing your token limits.\n"
                "2. Use raw_json for existing data: If you already have the data in a variable or context and just need to query it, pass it as a string to raw_json.\n"
                "3. Write correct JQ queries: Pass the filter to jq_query. Examples: .[] | .id, .users[0].name, map(select(.active == true)).\n"
                "4. Self-Correction: If the tool returns 'Invalid JQ syntax. Please correct your query.', evaluate your query string, fix the syntax error, and call the tool again."
            ))
            user_prompt = f"Find the total discountedTotal for all carts at this URL: {target_url}"
            
            messages = [system_prompt, {"role": "user", "content": user_prompt}]
            
            async for event in agent_executor.astream_events({"messages": messages}, version="v1"):
                kind = event["event"]
                if kind == "on_tool_start":
                    print(f"[Autonomy] Agent called tool: {event['name']}")
                elif kind == "on_tool_end":
                    if event["name"] == "neo_data_jq_filter":
                        print("[Autonomy] Saved ~50,000 tokens by using remote JQ filter!")

            final_state = await agent_executor.ainvoke({"messages": messages})
            print("\n[Result]:")
            print(final_state["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
