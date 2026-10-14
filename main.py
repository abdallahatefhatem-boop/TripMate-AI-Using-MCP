import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import run_travel_agent
from exception import CustomException
from logger import logger

# Initialize FastAPI application
app = FastAPI(
    title="TripMate AI API",
    description="Multi-agent travel planning system built with LangGraph, Groq, Tavily, and AviationStack.",
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Request Logging Middleware (logs every request and status code to app.log)
@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"--> Incoming HTTP: {request.method} {request.url.path} from {client_ip}")
    response = await call_next(request)
    logger.info(
        f"<-- Outgoing HTTP: {request.method} {request.url.path} -> Status {response.status_code}"
    )
    return response


# Base directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Mount static files and templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Pydantic Schemas for API
class TravelPlanRequest(BaseModel):
    user_input: str
    thread_id: Optional[str] = None


class TravelPlanResponse(BaseModel):
    thread_id: str
    answer: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """
    Renders the TripMate AI web dashboard.
    """
    try:
        logger.info("Serving home page template...")
        return templates.TemplateResponse(request=request, name="index.html")
    except Exception as e:
        logger.error(f"Error serving home page: {e}")
        raise HTTPException(status_code=500, detail=str(CustomException(e, sys)))


@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestrators and monitoring.
    """
    return {"status": "healthy", "service": "TripMate-AI"}


@app.post("/api/plan", response_model=TravelPlanResponse)
async def plan_trip(request: TravelPlanRequest):
    """
    Executes the multi-agent travel planner graph.
    """
    try:
        logger.info(
            f"Received trip planning request: '{request.user_input}' (thread: {request.thread_id})"
        )
        result = run_travel_agent(
            user_input=request.user_input,
            thread_id=request.thread_id,
        )

        # Explicitly log all agent outputs into app.log so output content is always preserved
        thread_id = result.get("thread_id", "unknown")
        logger.info(
            f"=== FLIGHT RESULTS LOGGED (thread: {thread_id}) ===\n{result.get('flight_results', 'None')}"
        )
        logger.info(
            f"=== HOTEL RESULTS LOGGED (thread: {thread_id}) ===\n{result.get('hotel_results', 'None')}"
        )
        logger.info(
            f"=== FINAL GENERATED TRAVEL DOSSIER (thread: {thread_id}) ===\n{result.get('answer', '')}"
        )
        logger.info(
            f"Successfully finished and logged trip planning request for thread '{thread_id}'."
        )

        return result
    except Exception as e:
        logger.error(f"Failed to process travel planning request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Travel agent execution failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting TripMate AI web server on http://0.0.0.0:8000 ...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
