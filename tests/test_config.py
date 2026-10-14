from configuration import ConfigurationManager
from entity import ModelConfig, PromptConfig


def test_configuration_manager_model_config():
    config_mgr = ConfigurationManager()
    model_cfg = config_mgr.get_model_config()

    assert isinstance(model_cfg, ModelConfig)
    assert model_cfg.provider == "groq"
    assert model_cfg.model_name in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]
    assert model_cfg.temperature == 0.5


def test_configuration_manager_prompt_config():
    config_mgr = ConfigurationManager()
    prompt_cfg = config_mgr.get_prompt_config()

    assert isinstance(prompt_cfg, PromptConfig)
    assert "expert travel planner" in prompt_cfg.itinerary_agent.system
    assert "travel booking assistant" in prompt_cfg.final_agent.system
    assert "{user_query}" in prompt_cfg.itinerary_agent.user_template
    assert "{itinerary}" in prompt_cfg.final_agent.user_template
