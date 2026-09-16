"""Proveedor externo OpenAI mediante Responses API."""

import asyncio
import time

import httpx

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.core.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTransientError,
)
from app.llm.base import BaseLLMProvider, LLMGeneration


class OpenAIProvider(BaseLLMProvider):
    """Cliente HTTP para Responses API con Structured Outputs."""

    provider = LLMProvider.OPENAI

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _extract_output_text(data: dict) -> str:
        """Extrae el texto de salida sin depender del SDK."""

        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content_item in item.get("content", []):
                if content_item.get("type") == "output_text":
                    text = content_item.get("text")
                    if isinstance(text, str) and text.strip():
                        return text

        raise LLMProviderError(
            "OpenAI no ha devuelto un bloque output_text utilizable."
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> LLMGeneration:
        if self.settings.openai_api_key is None:
            raise LLMConfigurationError(
                "Falta OPENAI_API_KEY en el archivo .env."
            )

        url = f"{self.settings.openai_base_url.rstrip('/')}/responses"
        headers = {
            "Authorization": (
                f"Bearer {self.settings.openai_api_key.get_secret_value()}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.openai_model,
            "instructions": system_prompt,
            "input": user_prompt,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "comunIA_triage",
                    "schema": json_schema,
                    "strict": True,
                }
            },
        }

        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds
        ) as client:
            for attempt in range(1, self.settings.max_retries + 1):
                started = time.perf_counter()

                try:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                    )
                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    error = LLMTransientError(
                        "Error temporal de conexión con OpenAI."
                    )
                    if attempt == self.settings.max_retries:
                        raise error from exc
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                latency_ms = (time.perf_counter() - started) * 1000

                if response.status_code == 429:
                    error = LLMRateLimitError(
                        "OpenAI ha aplicado un rate limit."
                    )
                    if attempt == self.settings.max_retries:
                        raise error
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 500:
                    error = LLMTransientError(
                        f"OpenAI ha devuelto {response.status_code}."
                    )
                    if attempt == self.settings.max_retries:
                        raise error
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 400:
                    raise LLMProviderError(
                        f"OpenAI ha rechazado la petición "
                        f"({response.status_code})."
                    )

                data = response.json()
                content = self._extract_output_text(data)
                usage = data.get("usage") or {}

                return LLMGeneration(
                    content=content,
                    model=str(data.get("model", self.settings.openai_model)),
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                    latency_ms=round(latency_ms, 2),
                )

        raise LLMProviderError("No se ha podido obtener respuesta de OpenAI.")
