# SPDX-License-Identifier: MIT
"""
LLM configuration settings for the application.
"""

from dataclasses import dataclass
import os
from fastlib.config import config_class, BaseConfig


@config_class("llm")
@dataclass
class LLMConfig(BaseConfig):
    """
    Configuration for LLM service connections.
    
    Attributes:
        model: LLM model identifier
        api_key: API key for authentication (from API_KEY env var)
        base_url: LLM API endpoint URL
    """
    
    model: str = "qwen-max"
    api_key: str = os.getenv("API_KEY", "sk-ed9faaf7609f494b9a106a33c4eac418")
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
