import asyncio, os, httpx
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
async def main():
    url = "https://mcp.neonia.io/mcp?tools=neo_web_json_fetch,neo_data_jq_filter"
    headers = {"Authorization": f"Bearer {os.getenv('NEONIA_API_KEY')}"} if os.getenv('NEONIA_API_KEY') else {}
    async with streamable_http_client(url, http_client=httpx.AsyncClient(headers=headers, timeout=60.0)) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            mcp_tools_response = await session.list_tools()
            print("Tools available:")
            for t in mcp_tools_response.tools:
                print(f"- {t.name}")
asyncio.run(main())
