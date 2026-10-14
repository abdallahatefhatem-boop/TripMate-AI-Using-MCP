import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from constant import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_PROVIDER,
    DEFAULT_TEMPERATURE,
    ENV_DATABASE_URL,
    MODEL_CONFIG_FILE_PATH,
    PROMPT_CONFIG_FILE_PATH,
)
from entity import (
    AgentPromptConfig,
    DatabaseConfig,
    ModelConfig,
    PromptConfig,
)
from exception import CustomException
from logger import logger

# Ensure environment variables are loaded
load_dotenv()


class ConfigurationManager:
    """
    Manages loading and parsing of project configuration files into typed entity objects.
    """

    def __init__(
        self,
        model_config_path: Path = MODEL_CONFIG_FILE_PATH,
        prompt_config_path: Path = PROMPT_CONFIG_FILE_PATH,
    ):
        self.model_config_path = model_config_path
        self.prompt_config_path = prompt_config_path

    def get_model_config(self) -> ModelConfig:
        """
        Loads and returns the ModelConfig entity from model_config.yaml.
        """
        try:
            logger.info(f"Loading model configuration from '{self.model_config_path}'")
            if not self.model_config_path.exists():
                logger.warning(
                    f"Model config file not found at '{self.model_config_path}'. Using defaults."
                )
                return ModelConfig(
                    provider=DEFAULT_MODEL_PROVIDER,
                    model_name=DEFAULT_MODEL_NAME,
                    temperature=DEFAULT_TEMPERATURE,
                )

            with open(self.model_config_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            model_data = content.get("model", {})
            config = ModelConfig(
                provider=model_data.get("provider", DEFAULT_MODEL_PROVIDER),
                model_name=model_data.get("model_name", DEFAULT_MODEL_NAME),
                temperature=float(model_data.get("temperature", DEFAULT_TEMPERATURE)),
                max_tokens=int(model_data.get("max_tokens", 4096)),
                max_retries=int(model_data.get("max_retries", 2)),
            )
            logger.info(
                f"ModelConfig loaded successfully: {config.model_name} (provider: {config.provider})"
            )
            return config

        except Exception as e:
            logger.error(f"Error loading model configuration: {e}")
            raise CustomException(e, sys)

    def get_prompt_config(self) -> PromptConfig:
        """
        Loads and returns the PromptConfig entity from prompt_config.yaml.
        """
        try:
            logger.info(f"Loading prompt configuration from '{self.prompt_config_path}'")
            if not self.prompt_config_path.exists():
                raise FileNotFoundError(f"Prompt config file missing at: {self.prompt_config_path}")

            with open(self.prompt_config_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            prompts_data = content.get("prompts", {})

            itin_data = prompts_data.get("itinerary_agent", {})
            final_data = prompts_data.get("final_agent", {})

            itinerary_prompt = AgentPromptConfig(
                system=itin_data.get("system", "You are an expert travel planner."),
                user_template=itin_data.get("user_template", "{user_query}"),
            )
            final_prompt = AgentPromptConfig(
                system=final_data.get(
                    "system", "You are a professional AI travel booking assistant."
                ),
                user_template=final_data.get("user_template", "{user_query}"),
            )

            prompt_config = PromptConfig(
                itinerary_agent=itinerary_prompt,
                final_agent=final_prompt,
            )
            logger.info("PromptConfig loaded successfully.")
            return prompt_config

        except Exception as e:
            logger.error(f"Error loading prompt configuration: {e}")
            raise CustomException(e, sys)

    def get_database_config(self) -> DatabaseConfig | None:
        """
        Resolves the PostgreSQL Database URL with sslmode requirement.
        """
        try:
            logger.info("Resolving PostgreSQL database configuration...")
            db_url = os.getenv(ENV_DATABASE_URL)
            if not db_url:
                logger.warning(
                    f"{ENV_DATABASE_URL} is missing. Please add your PostgreSQL URL to .env if persistence is required."
                )
                return None

            if "sslmode=" not in db_url:
                sep = "&" if "?" in db_url else "?"
                db_url = f"{db_url}{sep}sslmode=require"

            logger.info("DatabaseConfig resolved successfully.")
            return DatabaseConfig(database_url=db_url)

        except Exception as e:
            logger.error(f"Error resolving database configuration: {e}")
            raise CustomException(e, sys)
