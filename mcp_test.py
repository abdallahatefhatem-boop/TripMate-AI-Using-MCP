import asyncio

from mcp_project.mcp_client_test import tavily_mcp_search

if __name__ == "__main__":
    # asyncio.run(get_all_tools())
    asyncio.run(tavily_mcp_search(query="Latest news about AI"))
