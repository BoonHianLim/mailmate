from typing import AsyncIterator
import httpx
from loguru import logger

from .stateless_llm_interface import StatelessLLMInterface


class TestLLM(StatelessLLMInterface):
    def __init__(
            self,
            model: str = "test-model",
            base_url: str = None,
            llm_api_key: str = None,
            system: str = None,
    ):
        """
        Initialize Test LLM.

        Args:
            model (str): Model name
            base_url (str): Base URL for Test API
            llm_api_key (str): Test API key
            system (str): System prompt
        """
        self.model = model
        self.system = system

        # Initialize Test client
        self.client = None
        logger.info(f"Initialized Test LLM with model: {self.model}")

    async def chat_completion(self, messages, system=None, auth_uid: str = "") -> AsyncIterator[str]:
        url = "http://localhost:8101/assistant/chat"
        first_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
        payload = {
            "messages": first_user_message,
            "system": system
        }
        logger.info(f"Sending request to Test LLM: {payload}")

        cookies = {
            "key": auth_uid,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload, cookies=cookies) as response:
                async for line in response.aiter_lines():
                    if line.strip():  # optional: filter out empty lines
                        yield line
