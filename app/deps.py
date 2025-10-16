"""Dependency providers used by FastAPI endpoints.

This module exposes cached helpers to load docs, build the index, and
select an LLM provider based on environment variables.
"""

import os
from functools import lru_cache
import logging
from .data_loader import load_news
from .retriever import build_index
from .llm import MockLLM, OpenAILLM, LLMClient

NEWS_PATH_DEFAULT = os.getenv("NEWS_JSON_PATH", "stock_news.cleaned.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_docs():
    return load_news(NEWS_PATH_DEFAULT)

@lru_cache(maxsize=1)
def get_index():
    return build_index(get_docs())

# @lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    """
    Instantiate LLM client on each call so tests and env changes take effect.
    Use LLM_PROVIDER env var ("mock" or "openai").
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "openai":
        logger.info("get_llm -> OpenAILLM")
        return OpenAILLM()
    logger.info("get_llm -> MockLLM")
    return MockLLM()
    # return OpenAILLM() if (os.getenv("LLM_PROVIDER","mock").lower()=="openai") else MockLLM()
