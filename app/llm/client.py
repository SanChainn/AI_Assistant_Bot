"""
OpenRouter LLM client.

Provides async access to LLM models via the OpenRouter API.
Supports standard completion, streaming, and function/tool calling.
"""

from typing import AsyncGenerator, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class LLMClient:
    """
    Async HTTP client for OpenRouter API.

    Supports multiple models through a single interface.
    Default model: deepseek/deepseek-chat-v4-flash
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self._api_key = settings.OPENROUTER_API_KEY
        self._http = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ai-personal-assistant",
                "X-Title": "AI Personal Assistant",
            },
        )

    async def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a chat completion request to OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model identifier (default from settings).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0 - 2.0).
            tools: Optional list of tool specs for function calling.

        Returns:
            The full API response dict.
        """
        payload = {
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": temperature or settings.LLM_TEMPERATURE,
        }
        if tools:
            payload["tools"] = tools

        logger.debug(
            "LLM request: model=%s, messages=%d, tools=%s",
            payload["model"], len(messages), "yes" if tools else "no",
        )

        try:
            response = await self._http.post("/chat/completions", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.debug("LLM response received: %s", result.get("usage", {}))
            return result
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error %s: %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("LLM request failed: %s", e)
            raise

    async def chat_completion_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion response token by token.

        Yields individual content tokens as they arrive.
        """
        payload = {
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": temperature or settings.LLM_TEMPERATURE,
            "stream": True,
        }

        try:
            async with self._http.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
        except httpx.HTTPStatusError as e:
            logger.error("LLM stream error %s: %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("LLM stream request failed: %s", e)
            raise

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._http.aclose()


# Singleton instance
llm_client = LLMClient()