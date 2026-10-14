from dataclasses import dataclass


@dataclass
class ModelConfig:
    """
    Configuration entity for the LLM model.
    """

    provider: str
    model_name: str
    temperature: float = 0.5
    max_tokens: int = 4096
    max_retries: int = 2


@dataclass
class AgentPromptConfig:
    """
    Configuration entity for a single agent's prompt definitions.
    """

    system: str
    user_template: str


@dataclass
class PromptConfig:
    """
    Configuration entity holding prompts for all agents.
    """

    itinerary_agent: AgentPromptConfig
    final_agent: AgentPromptConfig


@dataclass
class DatabaseConfig:
    """
    Configuration entity for PostgreSQL connection.
    """

    database_url: str
    sslmode: str = "require"
