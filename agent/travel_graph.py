import os
import sys
import uuid

import certifi
from dotenv import load_dotenv

# Ensure SSL certificates are properly pointed for external API calls
load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from backend.schema.schema import TravelState
from configuration import ConfigurationManager
from constant import ENV_GROQ_API_KEY
from entity import TravelAgentOutput
from exception import CustomException
from logger import logger
from tools.flight_tool import search_flights
from tools.tavily_tool import tavily_search

# =====================================================================
# Configuration & LLM Initialization
# =====================================================================
try:
    logger.info("Initializing Agent configuration and LLM...")
    config_mgr = ConfigurationManager()
    model_cfg = config_mgr.get_model_config()
    prompt_cfg = config_mgr.get_prompt_config()
    db_cfg = config_mgr.get_database_config()

    groq_api_key = os.getenv(ENV_GROQ_API_KEY)
    if not groq_api_key:
        logger.warning(
            f"{ENV_GROQ_API_KEY} is missing from environment. Using placeholder for initialization."
        )

    llm = ChatGroq(
        model=model_cfg.model_name,
        api_key=groq_api_key or "gsk_placeholder_api_key_for_initialization",
        temperature=model_cfg.temperature,
        max_tokens=model_cfg.max_tokens,
        max_retries=model_cfg.max_retries,
    )
    logger.info(
        f"ChatGroq initialized successfully with model: {model_cfg.model_name} (max_tokens={model_cfg.max_tokens})"
    )

except Exception as e:
    logger.error(f"Error during agent setup/initialization: {e}")
    raise CustomException(e, sys)


# =====================================================================
# Node 1: Flight Agent
# =====================================================================
def flight_agent(state: TravelState) -> dict:
    try:
        query = state["user_query"]
        logger.info(f"[flight_agent] Searching flights for user query: '{query}'")
        flight_data = search_flights(query)
        logger.info("[flight_agent] Flight search completed successfully.")

        return {
            "flight_results": flight_data,
            "messages": [AIMessage(content="Flight results fetched.")],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
    except Exception as e:
        logger.error(f"[flight_agent] Error in flight_agent: {e}")
        raise CustomException(e, sys)


# =====================================================================
# Node 2: Hotel Agent
# =====================================================================
def hotel_agent(state: TravelState) -> dict:
    try:
        hotel_query = f"Best hotels for {state['user_query']}"
        logger.info(f"[hotel_agent] Searching hotels with query: '{hotel_query}'")
        hotel_results = tavily_search(hotel_query)
        logger.info("[hotel_agent] Hotel search completed successfully.")

        return {
            "hotel_results": hotel_results,
            "messages": [AIMessage(content="Hotel information fetched.")],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
    except Exception as e:
        logger.error(f"[hotel_agent] Error in hotel_agent: {e}")
        raise CustomException(e, sys)


# =====================================================================
# Node 3: Itinerary Agent
# =====================================================================
def itinerary_agent(state: TravelState) -> dict:
    try:
        logger.info("[itinerary_agent] Generating itinerary using LLM...")
        user_prompt = prompt_cfg.itinerary_agent.user_template.format(
            user_query=state.get("user_query", ""),
            flight_results=state.get("flight_results", ""),
            hotel_results=state.get("hotel_results", ""),
        )

        response = llm.invoke(
            [
                SystemMessage(content=prompt_cfg.itinerary_agent.system),
                HumanMessage(content=user_prompt),
            ]
        )
        logger.info("[itinerary_agent] Itinerary generated successfully.")

        return {
            "itinerary": response.content,
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
    except Exception as e:
        logger.error(f"[itinerary_agent] Error in itinerary_agent: {e}")
        raise CustomException(e, sys)


# =====================================================================
# Node 4: Final Response Agent
# =====================================================================
def final_agent(state: TravelState) -> dict:
    try:
        logger.info("[final_agent] Generating final structured response...")
        final_prompt = prompt_cfg.final_agent.user_template.format(
            user_query=state.get("user_query", ""),
            flight_results=state.get("flight_results", ""),
            hotel_results=state.get("hotel_results", ""),
            itinerary=state.get("itinerary", ""),
        )

        response = llm.invoke(
            [
                SystemMessage(content=prompt_cfg.final_agent.system),
                HumanMessage(content=final_prompt),
            ]
        )
        logger.info("[final_agent] Final response compiled successfully.")

        return {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
    except Exception as e:
        logger.error(f"[final_agent] Error in final_agent: {e}")
        raise CustomException(e, sys)


# =====================================================================
# Build Graph
# =====================================================================
try:
    logger.info("Constructing StateGraph workflow...")
    workflow = StateGraph(TravelState)

    workflow.add_node("flight_agent", flight_agent)
    workflow.add_node("hotel_agent", hotel_agent)
    workflow.add_node("itinerary_agent", itinerary_agent)
    workflow.add_node("final_agent", final_agent)

    workflow.add_edge(START, "flight_agent")
    workflow.add_edge("flight_agent", "hotel_agent")
    workflow.add_edge("hotel_agent", "itinerary_agent")
    workflow.add_edge("itinerary_agent", "final_agent")
    workflow.add_edge("final_agent", END)

    # Configure Checkpointer (PostgresSaver if DB configured, else InMemorySaver fallback)
    checkpointer = None
    if db_cfg and db_cfg.database_url:
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg.rows import dict_row

            logger.info("Attempting connection to PostgreSQL checkpointer...")
            conn = psycopg.connect(
                db_cfg.database_url,
                autocommit=True,
                row_factory=dict_row,
            )
            checkpointer = PostgresSaver(conn)
            checkpointer.setup()
            logger.info("PostgreSQL checkpointer configured and setup complete.")
        except Exception as db_err:
            logger.warning(
                f"Failed to initialize PostgreSQL checkpointer: {db_err}. Falling back to InMemorySaver."
            )
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
    else:
        logger.info("DATABASE_URL not supplied. Using InMemorySaver checkpointer.")
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

    travel_graph = workflow.compile(checkpointer=checkpointer)
    logger.info("Travel multi-agent graph compiled successfully.")

except Exception as e:
    logger.error(f"Error building travel_graph: {e}")
    raise CustomException(e, sys)


# =====================================================================
# Main Execution Function for FastAPI & CLI
# =====================================================================
def run_travel_agent(user_input: str, thread_id: str | None = None) -> dict:
    """
    Executes the travel planning agent graph for a given user query.
    """
    try:
        if not thread_id:
            thread_id = f"user_{uuid.uuid4().hex}"

        logger.info(f"Invoking travel_graph for thread_id='{thread_id}', query='{user_input}'")

        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }

        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0,
        }

        result = travel_graph.invoke(initial_state, config=config)

        final_answer = result["messages"][-1].content
        logger.info(
            f"Graph execution complete for thread_id='{thread_id}' with {result.get('llm_calls', 0)} calls."
        )
        logger.info(f"=== FULL FINAL DOSSIER FOR THREAD '{thread_id}' ===\n{final_answer}")

        output = TravelAgentOutput(
            thread_id=thread_id,
            answer=final_answer,
            flight_results=result.get("flight_results", ""),
            hotel_results=result.get("hotel_results", ""),
            itinerary=result.get("itinerary", ""),
            llm_calls=result.get("llm_calls", 0),
        )

        return {
            "thread_id": output.thread_id,
            "answer": output.answer,
            "flight_results": output.flight_results,
            "hotel_results": output.hotel_results,
            "itinerary": output.itinerary,
            "llm_calls": output.llm_calls,
        }

    except Exception as e:
        logger.error(f"Error running travel agent for query '{user_input}': {e}")
        raise CustomException(e, sys)
