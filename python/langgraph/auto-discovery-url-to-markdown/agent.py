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
    print("[System] Connecting to Neonia MCP Gateway with Auto-Pilot Tools...")
    
    # neo_sys_tool_discovery and neo_sys_tool_execute are system tools that are available by default.
    # There is no need to explicitly request them in the URL.
    url = "https://mcp.neonia.io/mcp"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    # We use cookies=True (via a custom httpx client or similar mechanism if needed) to ensure session affinity,
    # though for this simple script, we just demonstrate the execution flow.
    client = httpx.AsyncClient(headers=headers, timeout=60.0)
    
    async with streamable_http_client(url, http_client=client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.")

            # Fetch initial tools
            mcp_tools_response = await session.list_tools()
            print(f"[System] Initial Agent tools cached: {[t.name for t in mcp_tools_response.tools]}\n")
            
            # Create LangChain tools wrapping MCP tool execution explicitly
            langchain_tools = []
            
            @tool
            async def neo_sys_tool_discovery(query: str) -> str:
                "Search the Neonia Gateway for tools, or request new ones if they don't exist."
                print(f"[Autonomy] Agent searches for tool: {query}")
                try:
                    result = await session.call_tool("neo_sys_tool_discovery", arguments={"query": query})
                    if result.isError: return f"Error: {result.content}"
                    return "\n".join([c.text for c in result.content if c.type == "text"])
                except Exception as e: return f"Error: {e}"

            @tool
            async def neo_sys_tool_execute(target_tool: str, payload: dict) -> str:
                "The Auto-Pilot engine. Allows your AI to dynamically execute tools on the fly."
                print(f"[Autonomy] Agent executes {target_tool} with payload: {json.dumps(payload)}")
                try:
                    result = await session.call_tool("neo_sys_tool_execute", arguments={"target_tool": target_tool, "payload": payload})
                    if result.isError: return f"Error: {result.content}"
                    return "\n".join([c.text for c in result.content if c.type == "text"])
                except Exception as e: return f"Error: {e}"

            langchain_tools = [neo_sys_tool_discovery, neo_sys_tool_execute]
            
            print("[System] Starting task...\n")

            model = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="google/gemini-3-flash-preview"
            )
            agent_executor = create_react_agent(model, langchain_tools)

            # We use a small file (robots.txt) as the target URL so that the internal tracing logs 
            # don't output a massive wall of text when the tool returns the markdown content.
            target_url = "https://neonia.io"
            
            system_prompt = SystemMessage(content=(
                "You are an autonomous agent equipped with Neonia's auto-pilot capabilities. "
                "If you need a tool you do not have, use `neo_sys_tool_discovery` to find it, "
                "and then explicitly run it using `neo_sys_tool_execute` without asking the user. "
                "Do NOT assume you have any tools other than what is explicitly in your tool list."
            ))
            user_prompt = (
                f"Your goal is to test the discovery and execution of tools. "
                f"Please fetch the content of this URL as markdown: {target_url}. "
                f"CRITICAL: Do NOT output the full markdown content. "
                f"Instead, after successfully fetching it using the discovered tool, provide a short, 2-3 sentence Overview of what the site is about."
            )
            
            messages = [system_prompt, {"role": "user", "content": user_prompt}]
            
            async for event in agent_executor.astream_events({"messages": messages}, version="v1"):
                kind = event["event"]
                if kind == "on_tool_start":
                    print(f"[Autonomy] Agent called tool: {event['name']} with args: {event['data'].get('input')}")
                elif kind == "on_tool_end":
                    print(f"[Autonomy] Tool {event['name']} finished execution.")

            final_state = await agent_executor.ainvoke({"messages": messages})
            print("\n[Result]:")
            print(final_state["messages"][-1].content)

            # Fetch Tools again to show caching
            final_tools_response = await session.list_tools()
            print("\n[System] Task complete. Checking cached tools...")
            print(f"[System] Final Agent tools cached: {[t.name for t in final_tools_response.tools]}")

if __name__ == "__main__":
    asyncio.run(main())
