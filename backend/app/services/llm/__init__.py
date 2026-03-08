from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Credential
from app.services.encryption import decrypt_value


class LLMProvider(ABC):
    @abstractmethod
    async def stream(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def complete(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> str:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def stream(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> AsyncIterator[str]:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": config.get("model", "gpt-4o"),
                    "messages": all_messages,
                    "stream": True,
                    **{k: v for k, v in config.items() if k not in ["model"]},
                },
                timeout=60.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        data = json.loads(line[6:])
                        if delta := data.get("choices", [{}])[0].get("delta", {}).get("content"):
                            yield delta

    async def complete(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> str:
        result = ""
        async for chunk in self.stream(messages, system_prompt, config):
            result += chunk
        return result


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"

    async def stream(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "anthropic-dangerous-direct-browser-access": "true",
                },
                json={
                    "model": config.get("model", "claude-3-5-sonnet-20241022"),
                    "max_tokens": config.get("max_tokens", 4096),
                    "system": system_prompt,
                    "messages": messages,
                    "stream": True,
                },
                timeout=60.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            if delta := data.get("delta", {}).get("text"):
                                yield delta

    async def complete(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> str:
        result = ""
        async for chunk in self.stream(messages, system_prompt, config):
            result += chunk
        return result


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.ollama_base_url

    async def stream(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> AsyncIterator[str]:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": config.get("model", "qwen3:4b"),
                    "messages": all_messages,
                    "stream": True,
                },
                timeout=120.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if content := data.get("message", {}).get("content"):
                            yield content

    async def complete(
        self, messages: list[dict], system_prompt: str, config: dict
    ) -> str:
        result = ""
        async for chunk in self.stream(messages, system_prompt, config):
            result += chunk
        return result


async def get_provider(
    provider: str, session: AsyncSession, config: dict = None
) -> LLMProvider:
    config = config or {}
    
    if provider == "ollama":
        base_url = config.get("base_url", settings.ollama_base_url)
        return OllamaProvider(base_url)
    
    result = await session.execute(select(Credential).where(Credential.provider == provider))
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise ValueError(f"No API key configured for provider: {provider}")
    
    api_key = decrypt_value(credential.encrypted_key)
    
    if provider == "openai":
        return OpenAIProvider(api_key)
    elif provider == "anthropic":
        return AnthropicProvider(api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")
