import os
import sys

from dotenv import load_dotenv
from tavily import TavilyClient

from exception import CustomException
from logger import logger

try:
    logger.info("load Tavily API KEY..... ")
    load_dotenv()
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
except Exception as e:
    logger.error("There is trubile for tavily api key or not exist")
    raise CustomException(e, sys)

try:

    def tavily_search(query):
        response = client.search(
            query=query,
            max_results=5,  # return 5
        )

        results = []
        logger.info(
            "get title and url and content from json tavily response and appand them in list and return max_result =5"
        )
        for i, r in enumerate(response["results"], 1):
            title = r.get("title", "Unknown")  # get title from json response
            url = r.get("url", "")  # get url from json reponse
            snippet = r.get("content", "").strip()  # get content from ....
            # Keep only the first 300 characters to avoid wall-of-text
            if len(snippet) > 300:
                snippet = snippet[:300].rsplit(" ", 1)[0] + "..."

            results.append(f"{i}. **{title}**\n   {url}\n   {snippet}")

        return "\n\n".join(results)


except Exception as e:
    logger.error("there is something error in function tavily tool.")
    raise CustomException(e, sys)
