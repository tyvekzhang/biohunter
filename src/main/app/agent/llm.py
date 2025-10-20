from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo

from biodeepdiscovery.cohort.settings import settings


model_client = OpenAIChatCompletionClient(
    model=settings.llm.model,
    api_key=settings.llm.api_key,
    base_url=settings.llm.base_url,
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
