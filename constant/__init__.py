from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Config File Paths
CONFIG_DIR = PROJECT_ROOT / "configuration"
MODEL_CONFIG_FILE_PATH = CONFIG_DIR / "model_config.yaml"
PROMPT_CONFIG_FILE_PATH = CONFIG_DIR / "prompt_config.yaml"

# Default Model Constants
DEFAULT_MODEL_NAME = "qwen/qwen3.8-27b"
DEFAULT_MODEL_PROVIDER = "groq"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_RETRIES = 3

# Flight & Location Defaults
DEFAULT_ORIGIN_IATA = "DAC"
AVIATIONSTACK_BASE_URL = "https://api.aviationstack.com/v1/flights"

# Database & Environment Variable Keys
ENV_DATABASE_URL = "DATABASE_URL"
ENV_GROQ_API_KEY = "GROQ_API_KEY"
ENV_TAVILY_API_KEY = "TAVILY_API_KEY"
ENV_AVIATIONSTACK_API_KEY = "AVIATIONSTACK_API_KEY"
