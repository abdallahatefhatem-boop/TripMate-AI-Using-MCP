# 🌍 TripMate AI — Autonomous Multi-Agent Travel Planner

<div align="center">

---

## 📑 Table of Contents

1. [🌟 Overview & Problem Statement](#-overview--problem-statement)
2. [🧠 Multi-Agent Architecture (LangGraph Deep Dive)](#-multi-agent-architecture-langgraph-deep-dive)
3. [🛠️ Tool Implementations Under the Hood](#️-tool-implementations-under-the-hood)
4. [🔌 Model Context Protocol (MCP) Integration](#-model-context-protocol-mcp-integration)
5. [📐 Project Structure & Enterprise Design Patterns](#-project-structure--enterprise-design-patterns)
6. [⚙️ Environment Configuration & API Keys](#️-environment-configuration--api-keys)
7. [🚀 How to Run the Application & Web UI](#-how-to-run-the-application--web-ui)
   - [Method 1: Local Virtual Environment (Fastest)](#method-1-local-virtual-environment-fastest)
   - [Method 2: Using the Automation Makefile](#method-2-using-the-automation-makefile)
   - [Method 3: Docker & Docker Compose (Full Stack)](#method-3-docker--docker-compose-full-stack)
8. [🖥️ Interactive Web UI Walkthrough](#️-interactive-web-ui-walkthrough)
9. [📡 REST API Documentation](#-rest-api-documentation)
10. [🧪 Testing, Verification & Code Quality](#-testing-verification--code-quality)
11. [🛡️ Logging & Exception Diagnostics](#️-logging--exception-diagnostics)

---

## 🌟 Overview & Problem Statement

Planning an international vacation typically involves:

- Searching airline websites for live flight routes, baggage rules, terminal data, and schedules.
- Reading reviews across booking engines to discover top-rated accommodations that match a budget.
- Manually structuring daily sightseeing itineraries that balance travel time, activities, and rest.
- Tracking estimated costs across distinct currencies and categories.

**TripMate AI** automates this end-to-end process in seconds. By chaining specialized AI agents together using **LangGraph**, each agent is given a single responsibility (fetching flight telemetry, discovering hotels, designing daily itineraries, or consolidating the final financial budget), ensuring that real data anchors every single recommendation.

---

## 🧠 Multi-Agent Architecture (LangGraph Deep Dive)

The system is constructed as a deterministic **StateGraph** state machine. Each node reads from the shared `TravelState`, performs its specialized task, and outputs state updates.

<div align="center">

### 1. State Definition (`TravelState`)

Defined in [`backend/schema/schema.py`](./backend/schema/schema.py):

```python
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int
```

### 2. Graph Workflow Construction Code

From [`agent/travel_graph.py`](./agent/travel_graph.py):

```python
from langgraph.graph import StateGraph, START, END

# Initialize graph with state schema
workflow = StateGraph(TravelState)

# 1. Register specialized agent nodes
workflow.add_node("flight_agent", flight_agent)
workflow.add_node("hotel_agent", hotel_agent)
workflow.add_node("itinerary_agent", itinerary_agent)
workflow.add_node("final_agent", final_agent)

# 2. Define sequential execution edges
workflow.add_edge(START, "flight_agent")
workflow.add_edge("flight_agent", "hotel_agent")
workflow.add_edge("hotel_agent", "itinerary_agent")
workflow.add_edge("itinerary_agent", "final_agent")
workflow.add_edge("final_agent", END)

# 3. Compile graph with checkpointer (PostgresSaver or InMemorySaver)
travel_graph = workflow.compile(checkpointer=checkpointer)
```

### 3. Node Breakdown

| Node Name                     | Handler Function           | Role & Technology                                                                                                                                         |
| :---------------------------- | :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`flight_agent`**    | `flight_agent(state)`    | Parses the query, extracts origin and destination, resolves city/country names to 3-letter IATA codes (e.g. `DAC` -> `NRT`), and calls AviationStack. |
| **`hotel_agent`**     | `hotel_agent(state)`     | Queries Tavily Search with destination keywords to extract real hotels, locations, ratings, and amenities.                                                |
| **`itinerary_agent`** | `itinerary_agent(state)` | Ingests the flight telemetry and hotel listings, then prompts Groq (`qwen/qwen3.8-27b`) to construct an optimized day-by-day plan.                      |
| **`final_agent`**     | `final_agent(state)`     | Assembles the complete executive travel dossier with trip summary, flights, hotel recommendations, budget estimate, and tips.                             |

### 4. Checkpointing & State Persistence

- **PostgreSQL Checkpointer (`PostgresSaver`)**: If `DATABASE_URL` is set in your `.env` (e.g., Render, Supabase, Neon, or local Docker PostgreSQL), the graph automatically creates checkpoints for every execution thread (`thread_id`), allowing conversational resumption.
- **Graceful Fallback (`InMemorySaver`)**: If a database is not configured or offline during development, the engine automatically falls back to in-memory checkpointing without crashing.

---

## 🛠️ Tool Implementations Under the Hood

### 1. Flight Tool ([`tools/flight_tool.py`](./tools/flight_tool.py))

Resolving natural language locations into official IATA airport codes is accomplished via a 4-tier resolution pipeline:

1. **Direct IATA Matching**: Recognizes explicit 3-letter uppercase codes (e.g., `"DAC"`, `"LHR"`, `"JFK"`).
2. **Preferred City Hubs**: Maps major world capitals and travel hubs (e.g., `"dhaka"` -> `DAC`, `"tokyo"` -> `NRT`, `"london"` -> `LHR`, `"paris"` -> `CDG`).
3. **Country ISO Resolution**: Resolves country aliases via `pycountry` and maps them to primary international gateways (`COUNTRY_MAIN_AIRPORT`).
4. **Fuzzy Airport Database Scoring**: Searches `airportsdata` (7,800+ international airports), scoring candidates based on keyword matches (`"international"`, `"capital"`, city name matches).

Once resolved, it queries the **AviationStack API** and formats:

- Airline name and Flight number
- Flight status (`scheduled`, `active`, `landed`)
- Departure airport, terminal, gate, and delay in minutes
- Arrival airport, terminal, gate, and scheduled arrival time

### 2. Hotel Tool ([`tools/tavily_tool.py`](./tools/tavily_tool.py))

Connects to **Tavily AI Search**:

- Executes real-time targeted queries for accommodations matching the user's specific destination and budget.
- Filters and cleans snippets to prevent wall-of-text hallucination.
- Returns formatted titles, URLs, and summaries for the top 5 accommodations.

---

## 🔌 Model Context Protocol (MCP) Integration

TripMate AI has been upgraded with **Model Context Protocol (MCP)** support on top of the original architecture via [`mcp_project/`](./mcp_project/). This decouples tools into standardized, composable micro-servers managed through [`MultiServerMCPClient`](./mcp_project/mcp_client.py) from `langchain-mcp-adapters`, while preserving the legacy direct tool implementations for complete backward compatibility.

### 1. Integrated MCP Servers

| Server Name | Transport | Mechanism & Tools Provided |
| :--- | :--- | :--- |
| **`tavily`** | `streamable_http` | Direct HTTP streaming to `https://mcp.tavily.com/mcp/` providing `tavily_search`, `tavily_extract`, `tavily_crawl`, `tavily_map`, `tavily_research`. |
| **`aviationstack`** | `stdio` | Launched via `uvx aviationstack-mcp` with 13 live aviation tools (`get_flight_status`, `list_airports`, `list_airlines`, `list_routes`, etc.). |
| **`weather`** | `stdio` | Custom local FastMCP server ([`custom_weather_mcp_server.py`](./mcp_project/custom_weather_mcp_server.py)) calling OpenWeatherMap API for `get_current_weather` and `get_forecast`. |

### 2. Key MCP Features Added

- **Multi-Server Orchestration:** Independent server connections ensure that an outage or rate limit on one server (e.g. weather) does not block hotel search or flight planning.
- **Output Normalization:** Built-in [`format_mcp_output`](./mcp_project/mcp_client.py) handles raw MCP JSON payloads, converting them into clean markdown snippets formatted directly for LLM prompts.
- **Full Observability & Diagnostics:** Fully instrumented with the project's centralized [`logger`](./logger/__init__.py) and [`CustomException`](./exception/__init__.py), with timestamped file logging into `logs/`.
- **Backward Compatibility:** All original non-MCP tools in [`tools/`](./tools/) and previous graph functions remain preserved.

---

## 📐 Project Structure & Enterprise Design Patterns

The codebase adheres to modular, production-ready design principles:

```
my_venv/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline (Ruff linter & Pytest suite)
├── constant/
│   └── __init__.py              # Application constants, fallback values, and environment variable keys
├── configuration/
│   ├── model_config.yaml        # Decoupled LLM settings (qwen/qwen3.8-27b, temp, tokens)
│   ├── prompt_config.yaml       # Externalized prompts for Itinerary and Final agents
│   └── config_manager.py        # ConfigurationManager parsing YAML into strongly-typed entities
├── entity/
│   ├── config_entity.py         # Dataclasses: ModelConfig, PromptConfig, DatabaseConfig
│   └── artifact_entity.py       # Dataclasses: TravelAgentOutput, FlightArtifact, HotelArtifact
├── agent/
│   ├── __init__.py
│   └── travel_graph.py          # StateGraph orchestration, agent nodes, and PostgresSaver
├── backend/
│   └── schema/
│       └── schema.py            # TravelState TypedDict definition
├── mcp_project/
│   ├── __init__.py
│   ├── mcp_client.py            # MultiServerMCPClient manager, tool callers & normalizer
│   └── custom_weather_mcp_server.py # FastMCP stdio server for live weather & forecast
├── tools/
│   ├── flight_tool.py           # AviationStack live flight query & IATA resolution (legacy)
│   └── tavily_tool.py           # Tavily accommodation search tool (legacy)
├── logger/
│   └── __init__.py              # Dual console & timestamped file logger (logs/*.log)
├── exception/
│   └── __init__.py              # CustomException with script name and line number tracking
├── templates/
│   └── index.html               # Jinja2 modern Web Dashboard UI
├── static/
│   ├── css/style.css            # Dark glassmorphism styling, responsive layout & animations
│   └── js/main.js               # Frontend interactive controller & Markdown renderer
├── tests/
│   ├── test_api.py              # Tests for FastAPI endpoints (/ and /health)
│   ├── test_config.py           # Tests for YAML configuration loading and entities
│   ├── test_tools.py            # Tests for text cleaning, country lookup, and route parsing
│   └── test_graph.py            # Tests for LangGraph node registration and compilation
├── main.py                      # FastAPI web server and API endpoints
├── Dockerfile                   # Multi-stage production container
├── docker-compose.yml           # App + PostgreSQL container orchestration
├── Makefile                     # Developer command shortcuts (make run, make test, etc.)
└── pyproject.toml               # Dependency specification, Ruff & Pytest settings
```

---

## ⚙️ Environment Configuration & API Keys

Create a `.env` file in the root directory:

```env
# 1. Groq API Key (Fast LLM inference)
# Get a free key at: https://console.groq.com/keys
GROQ_API_KEY=gsk_your_groq_api_key_here

# 2. Tavily Search API Key (Hotel and web discovery / MCP)
# Get a free key at: https://app.tavily.com/
TAVILY_API_KEY=tvly-your_tavily_api_key_here

# 3. AviationStack API Key (Live flight telemetry / MCP)
# Get a free key at: https://aviationstack.com/
AVIATIONSTACK_API_KEY=your_aviationstack_api_key_here

# 4. OpenWeather API Key (Weather MCP server)
# Get a free key at: https://openweathermap.org/api
OPENWEATHER_API_KEY=your_openweather_api_key_here

# 5. Default Departure Airport Code (Optional, default is DAC)
DEFAULT_ORIGIN_IATA=DAC

# 6. PostgreSQL Database URL (Optional for conversation checkpointing)
# Example: postgresql://postgres:postgres@localhost:5432/tripmate
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tripmate
```

---

## 🚀 How to Run the Application & Web UI

### Method 1: Local Virtual Environment (Fastest)

1. **Activate the virtual environment**:

   ```bash
   source .venv/bin/activate
   ```
2. **Launch the web server**:

   ```bash
   python main.py
   ```

   *Or with live-reload using uvicorn:*

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Open the Web UI**:
   Navigate to: 👉 **[http://localhost:8000](http://localhost:8000)**

---

### Method 2: Using the Automation Makefile

The project includes pre-configured automation tasks:

```bash
# Run the FastAPI server and Web UI
make run

# Run all 10 unit tests
make test

# Run Ruff linter
make lint

# Auto-format Python code
make format

# Start Docker containers
make docker-up

# Stop Docker containers
make docker-down

# Clean caches and temporary logs
make clean
```

---

### Method 3: Docker & Docker Compose (Full Stack)

To launch the web app along with a dedicated PostgreSQL database container:

```bash
# Build and launch both containers in the background
docker compose up -d

# Stream logs in real time
docker compose logs -f

# Shut down containers and preserve database volume
docker compose down
```

---

## 🖥️ Interactive Web UI Walkthrough

The web dashboard is built with vanilla CSS and JavaScript for maximum performance, featuring a sleek **Dark Glassmorphism** design:

1. **Natural Language Query Box**:
   Enter your vacation idea directly, for example:

   - *"Plan a 7 days Japan trip from Bangladesh including hotels and sightseeing under budget"*
   - *"5 days vacation in Dubai with luxury hotels from London"*
   - *"Budget 4 days trip to Paris from New York"*
   - Or click any of the **Quick Suggestion Chips** right below the input box.
2. **Real-Time Animated Progress Stepper**:
   During execution, the UI displays an animated stepper that reflects the internal LangGraph state:

   - 🛫 *Scanning Live Flights (AviationStack)...*
   - 🏨 *Finding Top Hotels (Tavily)...*
   - 📅 *Synthesizing Daily Itinerary (Qwen 27B)...*
   - 📋 *Finalizing Travel Guide...*
3. **Tabbed Output Dashboard**:

   - **✨ Comprehensive Plan**: The complete dossier rendered in GitHub-flavored markdown with day-by-day schedules, highlights, and cost breakdown.
   - **🛫 Live Flights**: Clean telemetry showing airline names, flight numbers, terminals, gates, and live delay status.
   - **🏨 Hotel Options**: Discovered hotels with links, descriptions, and amenities.
   - **📅 Day-by-Day**: Focused daily itinerary.
   - **⚙️ Agent Metadata**: Technical execution details (Thread ID, total LLM calls, model name, and graph orchestrator).
4. **📋 Copy Plan**: Copies the full markdown output to your clipboard with one click.

---

## 📡 REST API Documentation

FastAPI automatically generates interactive Swagger documentation available at:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Key Endpoints

#### 1. Web Dashboard

- **Route**: `GET /`
- **Description**: Returns the rendered HTML dashboard interface.

#### 2. Health Check

- **Route**: `GET /health`
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "TripMate-AI"
  }
  ```

#### 3. Generate Travel Plan

- **Route**: `POST /api/plan`
- **Headers**: `Content-Type: application/json`
- **Request Payload**:
  ```json
  {
    "user_input": "Plan a 7 days trip to Tokyo from Dhaka under $2000",
    "thread_id": "optional-custom-session-id"
  }
  ```
- **Response Payload**:
  ```json
  {
    "thread_id": "user_2c6a4ff334b245029c4f552f3eab5668",
    "answer": "# 7-Day Tokyo Travel Plan\n\n### 1. Trip Summary...",
    "flight_results": "Airline: Biman Bangladesh Airlines\nFlight: BG091...",
    "hotel_results": "1. Hotel Gracery Shinjuku\n...",
    "itinerary": "Day 1: Arrival & Shinjuku...\nDay 2: Shibuya & Harajuku...",
    "llm_calls": 4
  }
  ```

---

## 🧪 Testing, Verification & Code Quality

The test suite covers API endpoints, configuration loading, location resolvers, and graph integrity:

```bash
make test
```

### Test Suite Summary (10 Passing Tests)

- `tests/test_api.py::test_home_page_endpoint`: Verifies HTML template rendering and 200 OK status.
- `tests/test_api.py::test_health_check_endpoint`: Verifies service health probe.
- `tests/test_config.py::test_configuration_manager_model_config`: Validates YAML model configuration parsing into `ModelConfig`.
- `tests/test_config.py::test_configuration_manager_prompt_config`: Validates external prompt templates.
- `tests/test_graph.py::test_graph_nodes_and_edges`: Verifies all 4 agent nodes are correctly registered in the StateGraph.
- `tests/test_graph.py::test_travel_graph_compilation`: Tests graph compilation with checkpointer attachment.
- `tests/test_tools.py::test_clean_text`: Verifies text normalization and stopword filtering.
- `tests/test_tools.py::test_country_name_to_code`: Tests ISO 3166-1 alpha-2 resolution (e.g., Japan -> `JP`).
- `tests/test_tools.py::test_resolve_location_to_iata`: Tests IATA mapping (e.g., Dhaka -> `DAC`, Tokyo -> `NRT`).
- `tests/test_tools.py::test_parse_route`: Tests origin-destination route extraction from natural queries.

---

## 🛡️ Logging & Exception Diagnostics

1. **Dual Console & File Logging**:
   Every event across all tools and agents is logged to both `sys.stdout` and a timestamped file under `logs/` (e.g. `logs/10_15_2026_00_00_30.log`):

   ```
   [2026-10-15 00:00:32,149] INFO [flight_tool.py:37] my_project - Step 1: Loaded 7884 airports into memory successfully.
   [2026-10-15 00:00:32,661] INFO [flight_tool.py:494] my_project - Step 8: Route parsed: dep=DAC, arr=NRT
   [2026-10-15 00:00:36,086] INFO [travel_graph.py:86] my_project - [hotel_agent] Hotel search completed successfully.
   [2026-10-15 00:00:51,447] INFO [travel_graph.py:245] my_project - Graph execution complete with 4 calls.
   ```
2. **Zero-Guesswork Exception Tracing**:
   Using `CustomException` from [`exception/__init__.py`](./exception/__init__.py), any runtime error automatically prints the file name and exact line number:

   ```
   Error occurred in script: [/home/mg/my_venv/agent/travel_graph.py] at line number: [141] error message: [...]
   ```
