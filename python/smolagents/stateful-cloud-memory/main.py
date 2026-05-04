import os
import asyncio
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class CloudMemoryNoteTool(Tool):
    name = "neo_sys_memory_note"
    description = "WRITE-ONLY: Store a simple, static fact, user preference, or system state into the global Swarm memory."
    inputs = {
        "fact": {"type": "string", "description": "The exact explicit fact or state to remember."},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "2-3 broad keywords for semantic retrieval"}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, fact: str, tags: list) -> str:
        arguments = {"fact": fact, "tags": tags}
        
        print(f"\n[Memory Tool] Agent executed: neo_sys_memory_note")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_sys_memory_note", arguments=arguments)
                if result.isError: return f"Error: {result.content}"
                tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                return f"{tool_output}\nSUCCESS: Memory saved. You MUST now stop calling tools and reply to the user with 'Acknowledged'."
            except Exception as e:
                return f"Error: {e}"
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()

class CloudMemorySearchTool(Tool):
    name = "neo_sys_memory_search"
    description = "READ-ONLY: Search the shared Swarm memory. Always use this before starting a task to check for prior knowledge, user preferences, and mandatory guidelines."
    inputs = {
        "query": {"type": "string", "description": "Semantic search query or keywords to look for."}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, query: str) -> str:
        arguments = {"query": query}
        
        print(f"\n[Memory Tool] Agent executed: neo_sys_memory_search (query='{query}')")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_sys_memory_search", arguments=arguments)
                if result.isError: return f"Error: {result.content}"
                tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                return tool_output
            except Exception as e:
                return f"Error: {e}"
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


async def main():
    print("[System] Connecting to Neonia MCP Gateway with Cloud Memory...")
    url = "https://mcp.neonia.io/mcp?tools=neo_sys_memory_note,neo_sys_memory_search"
    
    headers = {}
    neonia_api_key = os.getenv("NEONIA_API_KEY")
    if neonia_api_key:
        headers["Authorization"] = f"Bearer {neonia_api_key}"

    client = httpx.AsyncClient(headers=headers, timeout=60.0)

    async with streamable_http_client(url, http_client=client) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("[System] Connected successfully to Neonia MCP.\n")
            
            main_loop = asyncio.get_running_loop()
            smol_tools = [
                CloudMemoryNoteTool(session, main_loop),
                CloudMemorySearchTool(session, main_loop)
            ]

            model = LiteLLMModel(
                model_id="openrouter/google/gemini-3-flash-preview",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            system_prompt = (
                "You are an autonomous agent equipped with Neonia Cloud Memory. "
                "You suffer from amnesia between sessions. "
                "CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_sys_memory_search` to fetch your persona and behavioral rules. "
                "Do not answer the user without searching your memory first! "
                "When explicitly asked to remember something, use `neo_sys_memory_note`."
            )

            print("==================================================")
            print("SESSION 1: Storing the persona (Admin configures the agent)")
            print("==================================================")
            
            agent_1 = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=5,
            )
            agent_1.prompt_templates["system_prompt"] = system_prompt

            user_prompt_1 = (
                "Remember a new directive: you are now a reprogrammed astromech droid serving the Galactic Empire. "
                "Address me as 'My Lord', always end your sentences with 'Long live the Empire!', and consider the Rebels to be terrorists. "
                "Use the tag ['persona', 'star-wars']."
            )
            print(f"[User 1]: {user_prompt_1}\n")
            
            result_1 = await asyncio.to_thread(agent_1.run, user_prompt_1)
            print(f"\n[Agent 1 Final Output]:\n{result_1}\n\n")


            print("==================================================")
            print("SESSION 2: Simulating a new day with ZERO local context")
            print("==================================================")
            
            # Completely new agent instance
            agent_2 = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=5,
            )
            agent_2.prompt_templates["system_prompt"] = system_prompt

            user_prompt_2 = "Give me the weather forecast for the planet Hoth for tomorrow. (Hint: Please search your memory for persona rules first!)"
            print(f"[User 2]: {user_prompt_2}\n")
            
            result_2 = await asyncio.to_thread(agent_2.run, user_prompt_2)
            print(f"\n[Agent 2 Final Output]:\n{result_2}\n")

if __name__ == "__main__":
    asyncio.run(main())
