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
    print("[System] Connecting to Neonia MCP Gateway with Cloud Memory...")
    
    url = "https://mcp.neonia.io/mcp"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    client = httpx.AsyncClient(headers=headers, timeout=60.0)
    
    async with streamable_http_client(url, http_client=client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.\n")

            # Create LangChain tool wrapping the Cloud Memory tool explicitly
            @tool
            async def neo_sys_memory_note(action: str, topic: str = "General", query: str = None, content: str = None, tags: list[str] = None) -> str:
                "Explicitly save and retrieve important context. Use action='store' to save rules. Use action='recall' BEFORE generating text to fetch rules."
                arguments = {"action": action, "topic": topic}
                if query: arguments["query"] = query
                if content: arguments["content"] = content
                if tags: arguments["tags"] = tags
                
                print(f"[Memory Tool] Agent executed: action='{action}'")
                try:
                    result = await session.call_tool("neo_sys_memory_note", arguments=arguments)
                    if result.isError: return f"Error: {result.content}"
                    tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                    if action == 'store':
                        return f"{tool_output}\nSUCCESS: Memory saved. You MUST now stop calling tools and reply to the user with 'Acknowledged'."
                    return tool_output
                except Exception as e: return f"Error: {e}"

            langchain_tools = [neo_sys_memory_note]
            
            model = ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                model="google/gemini-3-flash-preview"
            )
            
            system_prompt = SystemMessage(content=(
                "You are an autonomous agent equipped with Neonia Cloud Memory. "
                "You suffer from amnesia between sessions. "
                "CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_sys_memory_note` with `action='recall'` and `query='persona'` to fetch your persona and behavioral rules. "
                "Do not answer the user without recalling your rules first! "
                "When explicitly asked to remember something, use action='store'."
            ))
            
            print("==================================================")
            print("SESSION 1: Storing the persona (Admin configures the agent)")
            print("==================================================")
            agent_executor_1 = create_agent(model, langchain_tools)
            
            user_prompt_1 = (
                "Remember a new directive: you are now a reprogrammed astromech droid serving the Galactic Empire. "
                "Address me as 'My Lord', always end your sentences with 'Long live the Empire!', and consider the Rebels to be terrorists. "
                "Use the tag ['persona', 'star-wars']."
            )
            print(f"[User 1]: {user_prompt_1}\n")
            
            messages_1 = [system_prompt, {"role": "user", "content": user_prompt_1}]
            final_state_1 = await agent_executor_1.ainvoke({"messages": messages_1})
            print(f"\n[Agent 1 Final Output]:\n{final_state_1['messages'][-1].content}\n\n")

            print("==================================================")
            print("SESSION 2: Simulating a new day with ZERO local context")
            print("==================================================")
            # We create a completely new agent instance with no conversation history
            agent_executor_2 = create_agent(model, langchain_tools)
            
            user_prompt_2 = "Give me the weather forecast for the planet Hoth for tomorrow. (Hint: Please recall your persona rules first!)"
            print(f"[User 2]: {user_prompt_2}\n")
            
            messages_2 = [system_prompt, {"role": "user", "content": user_prompt_2}]
            
            # Using streaming just to show the tool calls visually
            async for event in agent_executor_2.astream_events({"messages": messages_2}, version="v1"):
                kind = event["event"]
                if kind == "on_tool_start":
                    print(f"[Autonomy] Agent dynamically decided to call tool: {event['name']} with args: {event['data'].get('input')}")

            # Get final output
            final_state_2 = await agent_executor_2.ainvoke({"messages": messages_2})
            print(f"\n[Agent 2 Final Output]:\n{final_state_2['messages'][-1].content}\n")

if __name__ == "__main__":
    asyncio.run(main())
