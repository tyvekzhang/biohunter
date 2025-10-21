from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from fastlib import ConfigManager

from src.main.app.agent.config import LLMConfig

llm_config: LLMConfig = ConfigManager.get_config_instance("llm")
print(f"llm_config: {llm_config}")

model_client = OpenAIChatCompletionClient(
    model=llm_config.model,
    api_key=llm_config.api_key,
    base_url=llm_config.base_url,
    model_info=ModelInfo(
        vision=False,
        function_calling=True,
        json_output=True,
        family="unknown",
        structured_output=False,
    ),
    stream_options={"include_usage": True},
    parallel_tool_calls=False,
)
