# 🌍 TripMate AI — Autonomous Multi-Agent Travel Planner

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-FF4B4B?style=for-the-badge&logo=langchain&logoColor=white)
![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-4A154B?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Groq](https://img.shields.io/badge/Inference-Groq-F55036?style=for-the-badge)
![Docker](https://img.shields.io/badge/Container-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Ruff](https://img.shields.io/badge/Linter-Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

**An autonomous, multi-agent travel intelligence engine built with LangGraph, Groq, and the Model Context Protocol (MCP).**

![Workflow Demo](./2026-10-15%2000-23-55.gif)

</div>

---

## 📑 Table of Contents

1. [🌟 Overview & Key Capabilities](#-overview--key-capabilities)
2. [🧠 Multi-Agent Architecture (LangGraph Deep Dive)](#-multi-agent-architecture-langgraph-deep-dive)
3. [🔌 Model Context Protocol (MCP) Integration](#-model-context-protocol-mcp-integration)
4. [🛠️ Legacy Tools & Fallback Architecture](#️-legacy-tools--fallback-architecture)
5. [📐 Project Structure & Enterprise Design Patterns](#-project-structure--enterprise-design-patterns)
6. [⚙️ Environment Configuration & API Keys](#️-environment-configuration--api-keys)
7. [🚀 How to Run the Application](#-how-to-run-the-application)
   - [Method 1: Local Virtual Environment (uv)](#method-1-local-virtual-environment-uv)
   - [Method 2: Automation Makefile](#method-2-automation-makefile)
   - [Method 3: Docker & Docker Compose](#method-3-docker--docker-compose)
8. [🖥️ Interactive Web UI Dashboard](#️-interactive-web-ui-dashboard)
9. [📡 REST API & Swagger Documentation](#-rest-api--swagger-documentation)
10. [🔄 CI/CD Pipeline & GitHub Actions](#-cicd-pipeline--github-actions)
11. [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
12. [🛡️ Enterprise Logging & Exception Tracing](#️-enterprise-logging--exception-tracing)

---

## 🌟 Overview & Key Capabilities

Planning trips manually is time-consuming and fragmented across different airline schedules, hotel reviews, weather forecasts, and currency calculations. 

**TripMate AI** solves this by decomposing travel planning into a deterministic, specialized multi-agent workflow:

- 🛫 **Flight Intelligence:** Queries live aviation telemetry, airport codes, and route schedules via AviationStack.
- 🏨 **Accommodation Discovery:** Conducts real-time web discovery for hotels, ratings, and amenities via Tavily.
- ☀️ **Weather & Forecast:** Ingests live conditions and multi-day meteorological forecasts via OpenWeatherMap.
- 📅 **Day-by-Day Itineraries:** Generates realistic, geographically sensible daily plans balancing sightseeing with rest.
- 💰 **Budget & Travel Guidance:** Consolidates estimated airfare, hotel tiers, local tips, and seasonal warnings.

---

## 🧠 Multi-Agent Architecture (LangGraph Deep Dive)

The system is constructed as a deterministic **StateGraph** state machine. Each node reads from the shared `TravelState`, performs its specialized task using LLM reasoning or MCP tool invocations, and returns incremental state updates.

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

### 2. StateGraph Construction

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

# 2. Sequential execution pipeline
workflow.add_edge(START, "flight_agent")
workflow.add_edge("flight_agent", "hotel_agent")
workflow.add_edge("hotel_agent", "itinerary_agent")
workflow.add_edge("itinerary_agent", "final_agent")
workflow.add_edge("final_agent", END)

# 3. Compile graph with checkpointer (PostgresSaver or InMemorySaver)
travel_graph = workflow.compile(checkpointer=checkpointer)
```

### 3. Agent Nodes Breakdown

| Node Name | Handler Function | Technology & Execution |
| :--- | :--- | :--- |
| **`flight_agent`** | `flight_agent(state)` | Queries **AviationStack MCP** for airport catalogs and route data, formats prompts with telemetry, and invokes LLM for flight options. *(Legacy direct search preserved in comments).* |
| **`hotel_agent`** | `hotel_agent(state)` | Queries **Tavily MCP** (`streamable_http`) for real-time accommodation options matching query budget and destination. |
| **`itinerary_agent`** | `itinerary_agent(state)` | Ingests flight and hotel telemetry to construct an optimized day-by-day plan using Groq (`qwen/qwen3.8-27b`). |
| **`final_agent`** | `final_agent(state)` | Compiles the comprehensive travel dossier with trip summary, flight details, hotel links, itinerary, and estimated budget. |

### 4. Checkpointing & State Persistence

- **PostgreSQL Checkpointer (`PostgresSaver`)**: If `DATABASE_URL` is provided (local Docker, Supabase, Neon, etc.), every thread (`thread_id`) is persisted in PostgreSQL for multi-turn sessions.
- **In-Memory Fallback (`MemorySaver`)**: If database credentials are not configured, the system automatically falls back to in-memory state saving without crashing.

---

## 🔌 Model Context Protocol (MCP) Integration

TripMate AI has been upgraded with **Model Context Protocol (MCP)** support on top of the original architecture via [`mcp_project/`](./mcp_project/). This decouples external tools into standardized, composable micro-servers managed by [`MultiServerMCPClient`](./mcp_project/mcp_client.py) (`langchain-mcp-adapters`), while preserving the legacy direct tool implementations for complete backward compatibility.

### 1. Integrated MCP Servers

```
                       ┌────────────────────────┐
                       │  MultiServerMCPClient  │
                       └───────────┬────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      │                            │                            │
      ▼                            ▼                            ▼
┌─────────────┐             ┌─────────────┐             ┌─────────────┐
│   Tavily    │             │AviationStack│             │   Weather   │
│ Streamable  │             │ StdIO (uvx) │             │StdIO(Python)│
│    HTTP     │             │             │             │   FastMCP   │
└─────────────┘             └─────────────┘             └─────────────┘
```

| Server Name | Transport Protocol | Mechanism & Tools Provided |
| :--- | :--- | :--- |
| **`tavily`** | `streamable_http` | Direct HTTP streaming to `https://mcp.tavily.com/mcp/` providing `tavily_search`, `tavily_extract`, `tavily_crawl`, `tavily_map`, and `tavily_research`. |
| **`aviationstack`** | `stdio` | Launched via `uvx aviationstack-mcp` with 13 live aviation tools (`get_flight_status`, `list_airports`, `list_airlines`, `list_routes`, etc.). |
| **`weather`** | `stdio` | Custom local FastMCP server ([`custom_weather_mcp_server.py`](./mcp_project/custom_weather_mcp_server.py)) with OpenWeatherMap API for `get_current_weather` and `get_forecast`. |

### 2. Architectural Highlights of the MCP Implementation

- **Fault Isolation:** Each MCP server initializes on-demand. If an API key is restricted or an external service is unavailable, it does not prevent remaining servers from operating.
- **Output Normalization ([`format_mcp_output`](./mcp_project/mcp_client.py)):** Cleans raw MCP tool responses and JSON payloads into structured markdown snippets designed for direct consumption by LangGraph prompts.
- **Enterprise Observability:** Fully instrumented with the centralized [`logger`](./logger/__init__.py) and [`CustomException`](./exception/__init__.py) architecture.
- **Backward Compatibility:** All original non-MCP tools in [`tools/`](./tools/) and previous graph functions remain preserved in comments and modules.

---

## 🛠️ Legacy Tools & Fallback Architecture

For maximum resilience, the project preserves the original direct REST implementations:

### 1. Direct Flight Resolver ([`tools/flight_tool.py`](./tools/flight_tool.py))
- **4-Tier IATA Resolution:** Direct IATA code matching -> City main airports lookup (`CITY_MAIN_AIRPORT`) -> Country ISO resolution (`pycountry`) -> Database scoring (`airportsdata`, 7,800+ airports).
- Formats airline names, flight numbers, terminals, gates, scheduled departure/arrival, and live delay minutes.

### 2. Direct Tavily Search ([`tools/tavily_tool.py`](./tools/tavily_tool.py))
- Direct REST client using `tavily-python` returning top accommodation snippets.

---

## 📐 Project Structure & Enterprise Design Patterns

```
TripMate-AI/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI pipeline (Ruff linter & Pytest suite)
├── constant/
│   └── __init__.py              # Application constants & environment variable keys
├── configuration/
│   ├── model_config.yaml        # Decoupled LLM settings (qwen/qwen3.8-27b, temp, tokens)
│   ├── prompt_config.yaml       # Externalized prompts for Agent nodes
│   └── config_manager.py        # ConfigurationManager parsing YAML into typed entities
├── entity/
│   ├── config_entity.py         # Dataclasses: ModelConfig, PromptConfig, DatabaseConfig
│   └── artifact_entity.py       # Dataclasses: TravelAgentOutput, FlightArtifact, HotelArtifact
├── agent/
│   ├── __init__.py
│   └── travel_graph.py          # StateGraph orchestration, agent nodes & PostgresSaver
├── backend/
│   └── schema/
│       └── schema.py            # TravelState TypedDict schema definition
├── mcp_project/
│   ├── __init__.py
│   ├── mcp_client.py            # MultiServerMCPClient manager, tool callers & normalizer
│   ├── mcp_client_test.py       # Standalone MCP test client
│   └── custom_weather_mcp_server.py # FastMCP stdio server for live weather & forecast
├── tools/
│   ├── flight_tool.py           # AviationStack live flight query & IATA resolution (legacy)
│   └── tavily_tool.py           # Tavily accommodation search tool (legacy)
├── logger/
│   └── __init__.py              # Rotating file handler (logs/*.log) & stdout logger
├── exception/
│   └── __init__.py              # CustomException with script name & line number tracing
├── templates/
│   └── index.html               # Jinja2 modern Web Dashboard UI
├── static/
│   ├── css/style.css            # Dark glassmorphism styling, responsive layout & animations
│   ├── js/main.js               # Frontend interactive controller & Markdown renderer
│   └── images/                  # Architecture diagrams & UI assets
├── tests/
│   ├── test_api.py              # Tests for FastAPI endpoints (/ and /health)
│   ├── test_config.py           # Tests for YAML configuration loading and entities
│   ├── test_tools.py            # Tests for text cleaning, country lookup, and route parsing
│   └── test_graph.py            # Tests for LangGraph node registration and compilation
├── main.py                      # FastAPI web server, middleware & API endpoints
├── Dockerfile                   # Multi-stage production container with uv & uvx
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

# 2. Tavily Search API Key (Hotel discovery & MCP)
# Get a free key at: https://app.tavily.com/
TAVILY_API_KEY=tvly-your_tavily_api_key_here

# 3. AviationStack API Key (Live flight telemetry & MCP)
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

## 🚀 How to Run the Application

### Method 1: Local Virtual Environment (uv)

```bash
# 1. Install dependencies
uv sync

# 2. Start the FastAPI server
uv run python main.py

# Or run with live-reload:
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at: 👉 **[http://localhost:8000](http://localhost:8000)**

---

### Method 2: Automation Makefile

```bash
# Run the FastAPI server and Web UI
make run

# Run the 10-test unit test suite
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

### Method 3: Docker & Docker Compose

```bash
# Build and start web app + PostgreSQL in the background
docker compose up -d --build

# View real-time logs
docker compose logs -f web

# Shut down containers
docker compose down
```

---

## 🖥️ Interactive Web UI Dashboard

The UI is built with vanilla CSS and JavaScript with a modern **Dark Glassmorphism** design:

1. **Natural Language Input:** Users can enter complex travel requests:
   - *"Plan a 7 days Japan trip from Bangladesh including hotels and sightseeing under budget"*
   - *"5 days vacation in Dubai with luxury hotels from London"*
   - *"Budget 4 days trip to Paris from New York"*
2. **Animated State Stepper:** Visualizes the active LangGraph node in real time:
   - 🛫 *Scanning Live Flights (AviationStack MCP)...*
   - 🏨 *Discovering Accommodations (Tavily MCP)...*
   - 📅 *Synthesizing Daily Itinerary (Qwen 27B)...*
   - 📋 *Compiling Final Dossier...*
3. **Tabbed Dossier Dashboard:**
   - **✨ Comprehensive Plan:** Markdown-rendered complete itinerary with budget and advice.
   - **🛫 Live Flights:** Flight recommendations and airport route information.
   - **🏨 Hotel Options:** Real hotel recommendations with ratings and amenity details.
   - **📅 Day-by-Day:** Streamlined daily schedule breakdown.
   - **⚙️ Agent Metadata:** Execution metrics (Thread ID, total LLM calls, orchestrator).
4. **📋 One-Click Copy:** Copies the full plan to clipboard in formatted markdown.

---

## 📡 REST API & Swagger Documentation

Interactive Swagger documentation is available at: 👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Key Endpoints

#### 1. Web Dashboard
- **Route:** `GET /`
- **Response:** Rendered HTML dashboard interface.

#### 2. Health Check
- **Route:** `GET /health`
- **Response:**
  ```json
  {
    "status": "healthy",
    "service": "TripMate-AI"
  }
  ```

#### 3. Plan Trip
- **Route:** `POST /api/plan`
- **Payload:**
  ```json
  {
    "user_input": "Plan a 3 days trip to Paris from London",
    "thread_id": "optional-custom-session-id"
  }
  ```
- **Response:**
  ```json
  {
    "thread_id": "user_5a02788fcbf045c688cfcdc1e35b4c9e",
    "answer": "# 3-Day Paris Travel Plan\n\n### 1. Trip Summary...",
    "flight_results": "Live flight data...",
    "hotel_results": "1. Hotel Le 123 Sebastopol...",
    "itinerary": "Day 1: Arrival & Seine Cruise...",
    "llm_calls": 4
  }
  ```

---

## 🔄 CI/CD Pipeline & GitHub Actions

The repository includes an automated GitHub Actions workflow in [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) that triggers on every `push` and `pull_request` to `main`:

1. **Environment Setup:** Python 3.12 with pip cache.
2. **Dependency Installation:** `pip install -e .` with dev tools (`ruff`, `pytest`).
3. **Code Quality Linting:** `ruff check .`
4. **Formatting Check:** `ruff format --check .`
5. **Automated Unit Testing:** `pytest -v tests/` with mock API keys.

---

## 🧪 Testing & Quality Assurance

Run the unit test suite locally:

```bash
uv run pytest -v tests/
```

### Passing Test Suite (10 / 10 Tests)

| Test Identifier | Component | Verification Focus |
| :--- | :--- | :--- |
| `tests/test_api.py::test_home_page_endpoint` | Web API | Verifies template rendering and 200 OK status |
| `tests/test_api.py::test_health_check_endpoint` | Web API | Verifies container health probe |
| `tests/test_config.py::test_configuration_manager_model_config` | Config | Validates YAML model configuration loading |
| `tests/test_config.py::test_configuration_manager_prompt_config` | Config | Validates external agent prompt templates |
| `tests/test_graph.py::test_graph_nodes_and_edges` | LangGraph | Ensures all 4 agent nodes and transitions are registered |
| `tests/test_graph.py::test_travel_graph_compilation` | LangGraph | Confirms graph compilation with checkpointer |
| `tests/test_tools.py::test_clean_text` | Text Processing | Tests stopword filtering and normalization |
| `tests/test_tools.py::test_country_name_to_code` | Resolver | Tests ISO 3166-1 alpha-2 resolution |
| `tests/test_tools.py::test_resolve_location_to_iata` | Resolver | Tests natural text to 3-letter IATA resolution |
| `tests/test_tools.py::test_parse_route` | Resolver | Tests departure and arrival pair extraction |

---

## 🛡️ Enterprise Logging & Exception Tracing

### 1. Centralized Logging (`logger/`)
- Logs to both standard output and rotating files (`logs/app_YYYY-MM-DD_HH-MM-SS.log`).
- Formatted with timestamp, log level, filename, line number, and component name.
- Uvicorn access and HTTP requests are captured in the same file for unified troubleshooting.

### 2. Zero-Guesswork Exception Handling (`exception/`)
- Powered by `CustomException`, which dynamically extracts the traceback frame:
  ```
  Error occurred in script: [/app/agent/travel_graph.py] at line number: [141] error message: [...]
  ```
- Eliminates ambiguous errors by logging exact execution lines across threads and async tasks.

---

<div align="center">

**TripMate AI** — Engineered for autonomous travel planning with production-grade AI agent orchestration.

</div>
