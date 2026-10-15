import json
import os
import sys
from pathlib import Path

import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

from exception import CustomException
from logger import logger

# ==========================================
# Environment configuration
# ==========================================
try:
    logger.info("Initializing MCP environment and loading configuration...")
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

    load_dotenv()

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY is missing from environment.")
    else:
        logger.info("TAVILY_API_KEY loaded successfully.")

    if not AVIATION_STACK_API_KEY:
        logger.warning("AVIATIONSTACK_API_KEY is missing from environment.")
    else:
        logger.info("AVIATIONSTACK_API_KEY loaded successfully.")

    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is missing from environment.")
    else:
        logger.info("GROQ_API_KEY loaded successfully.")

    # Automatically find the current project folder.
    # This replaces the hard-coded Windows paths.
    PROJECT_DIR = Path(__file__).resolve().parent
    WEATHER_SERVER_PATH = PROJECT_DIR / "custom_weather_mcp_server.py"

    # Preserve the complete Windows environment when starting
    # local stdio MCP servers.
    AVIATION_ENV = os.environ.copy()
    AVIATION_ENV["AVIATION_STACK_API_KEY"] = AVIATION_STACK_API_KEY or ""

    WEATHER_ENV = os.environ.copy()
    WEATHER_ENV["OPENWEATHER_API_KEY"] = OPENWEATHER_API_KEY or ""
    logger.info("Environment configuration completed.")

except Exception as e:
    logger.error(f"Error during MCP client environment configuration: {e}")
    raise CustomException(e, sys)


# ==========================================
# LLM
# ==========================================
try:
    logger.info("Initializing ChatGroq LLM for MCP client...")
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY or "gsk_placeholder_api_key_for_initialization",
    )
    logger.info("ChatGroq LLM initialized successfully.")
except Exception as e:
    logger.error(f"Error during ChatGroq initialization: {e}")
    raise CustomException(e, sys)


# ==========================================
# MCP client configuration
# ==========================================
try:
    logger.info("Configuring MultiServerMCPClient servers...")
    client = MultiServerMCPClient(
        {
            "tavily": {
                "transport": "streamable_http",
                "url": (f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"),
            },
            "aviationstack": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["aviationstack-mcp"],
                "env": AVIATION_ENV,
            },
            "weather": {
                "transport": "stdio",
                # Use the same Python environment that runs app.py.
                "command": sys.executable,
                # Automatically use custom_weather_mcp_server.py
                # from the current project directory.
                "args": [str(WEATHER_SERVER_PATH)],
                "env": WEATHER_ENV,
            },
        }
    )
    logger.info("MultiServerMCPClient configured successfully.")
except Exception as e:
    logger.error(f"Error configuring MultiServerMCPClient: {e}")
    raise CustomException(e, sys)


# ==========================================
# MCP Output Normalizer
# ==========================================
def format_mcp_output(result) -> str:
    """
    Format and clean MCP results into readable string content.
    Handles Tavily search results json structures, lists of text blocks,
    and plain strings.
    """
    try:
        if isinstance(result, list):
            formatted_parts = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    raw_text = item["text"]
                    try:
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict) and "results" in parsed:
                            snippets = []
                            for idx, r in enumerate(parsed["results"], 1):
                                title = r.get("title", "Unknown")
                                url = r.get("url", "")
                                content = r.get("content", "").strip()
                                if len(content) > 300:
                                    content = content[:300].rsplit(" ", 1)[0] + "..."
                                snippets.append(f"{idx}. **{title}**\n   {url}\n   {content}")
                            formatted_parts.append("\n\n".join(snippets))
                        else:
                            formatted_parts.append(raw_text)
                    except (json.JSONDecodeError, TypeError):
                        formatted_parts.append(raw_text)
                elif hasattr(item, "content"):
                    formatted_parts.append(str(item.content))
                else:
                    formatted_parts.append(str(item))
            return "\n\n".join(formatted_parts)

        if isinstance(result, dict):
            if "text" in result:
                return result["text"]
            return json.dumps(result, ensure_ascii=False)

        return str(result)
    except Exception as e:
        logger.warning(f"Error formatting MCP output: {e}. Returning raw str.")
        return str(result)


# ==========================================
# Diagnostic function
# ==========================================


async def get_all_tools():
    """
    Load each MCP server separately.

    A broken server will no longer prevent the other
    working servers from loading.
    """
    logger.info("Starting diagnostic check: retrieving tools from all MCP servers...")
    all_tools = []

    for server_name in ("tavily", "aviationstack", "weather"):
        try:
            tools = await client.get_tools(server_name=server_name)

            all_tools.extend(tools)

            logger.info(
                f"Successfully connected to {server_name} MCP. "
                f"Found {len(tools)} tools: {[t.name for t in tools]}"
            )

            print(f"\nAvailable tools from {server_name} MCP:\n")

            for tool in tools:
                print(tool.name)

        except Exception as error:
            logger.error(f"Could not connect to {server_name} MCP: {error}")
            print(f"\nCould not connect to {server_name} MCP:\n{error}\n")

    return all_tools


# ==========================================
# Tavily MCP tool
# ==========================================

search_tool = None


async def initialize_mcp():
    """
    Initialize only Tavily.

    Previously this function initialized all MCP servers,
    so an AviationStack or Weather failure also caused
    Tavily hotel search to fail.
    """

    global search_tool

    if search_tool is not None:
        return

    try:
        logger.info("Initializing Tavily MCP search tool...")
        tools = await client.get_tools(server_name="tavily")

        tools_by_name = {tool.name: tool for tool in tools}

        search_tool = tools_by_name.get("tavily_search")

        if search_tool is None:
            available_tools = ", ".join(tools_by_name.keys())

            err_msg = (
                "Tavily MCP connected, but the "
                "'tavily_search' tool was not found. "
                f"Available tools: "
                f"{available_tools or 'none'}"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info("Tavily MCP 'tavily_search' tool initialized successfully.")

    except Exception as e:
        logger.error(f"Error initializing Tavily MCP: {e}")
        raise CustomException(e, sys)


async def tavily_mcp_search(query: str) -> str:
    """
    Search web/hotels using Tavily MCP server and return formatted results.
    """
    try:
        logger.info(f"Executing Tavily MCP search for query: '{query}'")
        await initialize_mcp()

        result = await search_tool.ainvoke({"query": query})

        formatted_result = format_mcp_output(result)
        logger.info("Tavily MCP search completed successfully.")
        return formatted_result

    except Exception as e:
        logger.error(f"Error during Tavily MCP search for query '{query}': {e}")
        raise CustomException(e, sys)


# ==========================================
# AviationStack MCP tools
# ==========================================

aviation_tools = {}


async def initialize_aviation_tools():
    global aviation_tools

    if aviation_tools:
        return

    try:
        logger.info("Initializing AviationStack MCP tools...")
        # Load only AviationStack.
        # Tavily and Weather will not be initialized here.
        tools = await client.get_tools(server_name="aviationstack")

        aviation_tools = {tool.name: tool for tool in tools}

        if not aviation_tools:
            err_msg = "AviationStack MCP connected but returned no tools."
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info(
            f"AviationStack MCP tools initialized successfully. "
            f"Available tools: {list(aviation_tools.keys())}"
        )

    except Exception as e:
        logger.error(f"Error initializing AviationStack MCP tools: {e}")
        raise CustomException(e, sys)


async def aviation_mcp_call(tool_name: str, tool_args: dict = None):
    """
    Execute any AviationStack MCP tool by name.
    """
    try:
        logger.info(f"Calling AviationStack MCP tool '{tool_name}' with args: {tool_args}")
        await initialize_aviation_tools()

        tool = aviation_tools.get(tool_name)

        if tool is None:
            available_tools = ", ".join(sorted(aviation_tools.keys()))

            err_msg = (
                f"AviationStack tool '{tool_name}' "
                "was not found. "
                f"Available tools: "
                f"{available_tools or 'none'}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)

        result = await tool.ainvoke(tool_args or {})

        formatted = format_mcp_output(result)
        logger.info(f"AviationStack MCP tool '{tool_name}' completed successfully.")
        return formatted

    except Exception as e:
        logger.error(f"Error executing AviationStack MCP tool '{tool_name}': {e}")
        raise CustomException(e, sys)


# ==========================================
# Weather MCP tools
# ==========================================

weather_tool = None
forecast_tool = None


async def initialize_weather_tools():
    global weather_tool
    global forecast_tool

    if weather_tool is not None and forecast_tool is not None:
        return

    try:
        logger.info("Initializing Weather MCP tools...")
        if not WEATHER_SERVER_PATH.exists():
            err_msg = f"Weather MCP server file was not found: {WEATHER_SERVER_PATH}"
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)

        # Load only Weather.
        # Tavily and AviationStack will not be started.
        tools = await client.get_tools(server_name="weather")

        tools_by_name = {tool.name: tool for tool in tools}

        weather_tool = tools_by_name.get("get_current_weather")

        forecast_tool = tools_by_name.get("get_forecast")

        missing_tools = []

        if weather_tool is None:
            missing_tools.append("get_current_weather")

        if forecast_tool is None:
            missing_tools.append("get_forecast")

        if missing_tools:
            available_tools = ", ".join(tools_by_name.keys())

            err_msg = (
                "Missing Weather MCP tools: "
                f"{', '.join(missing_tools)}. "
                f"Available tools: "
                f"{available_tools or 'none'}"
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info("Weather MCP tools initialized successfully.")

    except Exception as e:
        logger.error(f"Error initializing Weather MCP tools: {e}")
        raise CustomException(e, sys)


async def weather_mcp_search(city: str) -> str:
    """
    Fetch current weather for a city using Weather MCP server.
    """
    try:
        logger.info(f"Executing Weather MCP search for city: '{city}'")
        await initialize_weather_tools()

        result = await weather_tool.ainvoke({"city": city})

        formatted = format_mcp_output(result)
        logger.info(f"Weather MCP search for '{city}' completed successfully.")
        return formatted

    except Exception as e:
        logger.error(f"Error during weather_mcp_search for '{city}': {e}")
        raise CustomException(e, sys)


async def forecast_mcp_search(city: str) -> str:
    """
    Fetch 5-day forecast for a city using Weather MCP server.
    """
    try:
        logger.info(f"Executing Forecast MCP search for city: '{city}'")
        await initialize_weather_tools()

        result = await forecast_tool.ainvoke({"city": city})

        formatted = format_mcp_output(result)
        logger.info(f"Forecast MCP search for '{city}' completed successfully.")
        return formatted

    except Exception as e:
        logger.error(f"Error during forecast_mcp_search for '{city}': {e}")
        raise CustomException(e, sys)


# ==========================================
# Destination extractor
# ==========================================


def extract_destination(query: str) -> str:
    """
    Extract destination city or country name from query using LLM.
    """
    try:
        logger.info(f"Extracting destination from query: '{query}'")
        prompt = f"""
        Extract only the destination city or country.

        Query:
        {query}

        Return only destination name.
        """

        response = llm.invoke(prompt)
        destination = response.content.strip()
        logger.info(f"Destination extracted: '{destination}'")
        return destination

    except Exception as e:
        logger.error(f"Error in extract_destination for query '{query}': {e}")
        raise CustomException(e, sys)


# ==========================================
# Standalone execution / verification
# ==========================================
if __name__ == "__main__":
    import asyncio

    try:
        logger.info("Running mcp_client.py standalone diagnostic test...")
        asyncio.run(get_all_tools())
        logger.info("mcp_client.py standalone test completed successfully.")
    except Exception as e:
        logger.error(f"Error in mcp_client.py standalone execution: {e}")
        raise CustomException(e, sys)
