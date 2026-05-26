"""OpenRouter API client for chat completions."""

import os
from typing import Any

import httpx


class OpenRouterClient:
    """LLM client for OpenRouter API with multi-model support."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat completion request.

        Returns:
            dict with keys: content, model, usage.
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        with httpx.Client(base_url=self.BASE_URL, timeout=60) as client:
            resp = client.post(
                "/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "model": model,
                "usage": data.get("usage", {}),
            }
