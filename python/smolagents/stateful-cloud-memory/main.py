import os
import asyncio
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class CloudMemoryTool(Tool):
    name = "neo_agent_cloud_memory"
    description = "Explicitly save and retrieve important context. Use action='store' to save rules. Use action='recall' BEFORE generating text to fetch rules."
    inputs = {
        "action": {"type": "string", "description": "The action to perform: store, recall, forget, or list_tags"},
        "topic": {"type": "string", "description": "A short string identifying the topic of the memory (required for store).", "nullable": True},
        "query": {"type": "string", "description": "Search query for recall", "nullable": True},
        "content": {"type": "string", "description": "Content to save for store", "nullable": True},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to classify the memory", "nullable": True}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, action: str, topic: str = "General", query: str = None, content: str = None, tags: list = None) -> str:
        arguments = {"action": action}
        if topic: arguments["topic"] = topic
        if query: arguments["query"] = query
        if content: arguments["content"] = content
        if tags: arguments["tags"] = tags
        
        print(f"\n[Memory Tool] Agent executed: action='{action}'")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_agent_cloud_memory", arguments=arguments)
                if result.isError: return f"Error: {result.content}"
                tool_output = "\n".join([c.text for c in result.content if c.type == "text"])
                if action == 'store':
                    return f"{tool_output}\nSUCCESS: Memory saved. You MUST now stop calling tools and reply to the user with 'Acknowledged'."
                return tool_output
            except Exception as e:
                return f"Error: {e}"
        
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(call_mcp(), self.loop)
        return future.result()


async def main():
    print("[System] Connecting to Neonia MCP Gateway with Cloud Memory...")
    url = "https://mcp.neonia.io/mcp?tools=neo_agent_cloud_memory"
    
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
                CloudMemoryTool(session, main_loop)
            ]

            model = LiteLLMModel(
                model_id="openrouter/google/gemini-3-flash-preview",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            system_prompt = (
                "You are an autonomous agent equipped with Neonia Cloud Memory. "
                "You suffer from amnesia between sessions. "
                "CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_agent_cloud_memory` with `action='recall'` and `query='persona'` to fetch your persona and behavioral rules. "
                "Do not answer the user without recalling your rules first! "
                "When explicitly asked to remember something, use action='store'."
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

            user_prompt_2 = "Give me the weather forecast for the planet Hoth for tomorrow. (Hint: Please recall your persona rules first!)"
            print(f"[User 2]: {user_prompt_2}\n")
            
            result_2 = await asyncio.to_thread(agent_2.run, user_prompt_2)
            print(f"\n[Agent 2 Final Output]:\n{result_2}\n")

if __name__ == "__main__":
    asyncio.run(main())
