# SPDX-License-Identifier: MIT
"""
LLM configuration settings for the application.
"""

from dataclasses import dataclass
import os
from fastlib.config.base import BaseConfig
from fastlib.config.manager import config_class


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
    api_key: str = os.getenv("API_KEY")
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"