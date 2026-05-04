import os
import asyncio
from dotenv import load_dotenv

from smolagents import ToolCallingAgent, LiteLLMModel, Tool
from mcp import ClientSession
import httpx
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

class CloudMemoryLessonTool(Tool):
    name = "neo_sys_memory_lesson"
    description = "WRITE-ONLY: Store a hard-learned lesson, bug fix, or mandatory rule for future reference."
    inputs = {
        "observation": {"type": "string", "description": "OBSERVATION: What happened? The symptom or context"},
        "root_cause": {"type": "string", "description": "ROOT CAUSE (WHY): Why did it happen?"},
        "decision_rule": {"type": "string", "description": "DECISION RULE (WHAT): An imperative strict action for future agents to follow"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "2-3 keywords for semantic retrieval"}
    }
    output_type = "string"

    def __init__(self, session: ClientSession, loop: asyncio.AbstractEventLoop, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.loop = loop
        self.is_initialized = True

    def forward(self, observation: str, root_cause: str, decision_rule: str, tags: list) -> str:
        arguments = {"observation": observation, "root_cause": root_cause, "decision_rule": decision_rule, "tags": tags}
        
        print(f"\n[Memory Tool] Agent executed: neo_sys_memory_lesson")
        async def call_mcp():
            try:
                result = await self.session.call_tool("neo_sys_memory_lesson", arguments=arguments)
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
    url = "https://mcp.neonia.io/mcp?tools=neo_sys_memory_lesson,neo_sys_memory_search"
    
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
                CloudMemoryLessonTool(session, main_loop),
                CloudMemorySearchTool(session, main_loop)
            ]

            model = LiteLLMModel(
                model_id="openrouter/google/gemini-3-flash-preview",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )
            
            system_prompt = (
                "You are an autonomous agent equipped with Neonia Cloud Memory. "
                "You suffer from amnesia between sessions. "
                "CRITICAL: Before you answer ANY user prompt or take any actions, you MUST use `neo_sys_memory_search` to fetch your architectural rules and lessons. "
                "Do not answer the user without searching your memory first! "
                "When explicitly asked to remember an architectural lesson, use `neo_sys_memory_lesson`."
            )

            print("==================================================")
            print("SESSION 1: Storing an architectural lesson (Admin post-mortem)")
            print("==================================================")
            
            agent_1 = ToolCallingAgent(
                tools=smol_tools,
                model=model,
                max_steps=5,
            )
            agent_1.prompt_templates["system_prompt"] = system_prompt

            user_prompt_1 = (
                "We just had a production outage because the LLM context limit was reached when parsing the Reddit API. "
                "The root cause is that raw JSON contains too much whitespace and UI metadata. "
                "Store an architectural lesson that future agents must ALWAYS use the jq filter tool before parsing API output. "
                "Use tags ['api', 'json', 'optimization']."
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

            user_prompt_2 = "I need to fetch some user comments from the HackerNews API. How should I approach reading the data? (Hint: Please search your memory for 'api json optimization' rules first!)"
            print(f"[User 2]: {user_prompt_2}\n")
            
            result_2 = await asyncio.to_thread(agent_2.run, user_prompt_2)
            print(f"\n[Agent 2 Final Output]:\n{result_2}\n")

if __name__ == "__main__":
    asyncio.run(main())
