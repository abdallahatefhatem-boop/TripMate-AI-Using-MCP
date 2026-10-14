# from logger import logger
# from tools.tavily_tool import tavily_search

# query = "What is the best player soccer in the history?"
# res = tavily_search(query)
# logger.info(f"Tavily Search Results for '{query}':\n{res}")

from tools.flight_tool import search_flights

res=search_flights("plan a 7 days japan trip from Bangladesh")
print(res)