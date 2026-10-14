from logger import logger
from tools.tavily_tool import tavily_search

query = "What is the best player soccer in the history?"
res = tavily_search(query)
logger.info(f"Tavily Search Results for '{query}':\n{res}")