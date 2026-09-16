"""Proveedor local Ollama."""

import asyncio
import time

import httpx

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.core.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMTransientError,
)
from app.llm.base import BaseLLMProvider, LLMGeneration


class OllamaProvider(BaseLLMProvider):
    """Cliente mínimo para la API HTTP local de Ollama."""

    provider = LLMProvider.OLLAMA

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> LLMGeneration:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"

        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": json_schema,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
                "top_p": self.settings.top_p,
            },
        }

        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds
        ) as client:
            for attempt in range(1, self.settings.max_retries + 1):
                started = time.perf_counter()

                try:
                    response = await client.post(url, json=payload)
                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    error = LLMTransientError(
                        "No se ha podido conectar temporalmente con Ollama."
                    )
                    if attempt == self.settings.max_retries:
                        raise error from exc
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                latency_ms = (time.perf_counter() - started) * 1000

                if response.status_code == 429:
                    error = LLMRateLimitError(
                        "Ollama ha limitado temporalmente las peticiones."
                    )
                    if attempt == self.settings.max_retries:
                        raise error
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 500:
                    error = LLMTransientError(
                        f"Ollama ha devuelto {response.status_code}."
                    )
                    if attempt == self.settings.max_retries:
                        raise error
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 400:
                    raise LLMProviderError(
                        f"Ollama ha rechazado la petición "
                        f"({response.status_code})."
                    )

                data = response.json()

                try:
                    content = data["message"]["content"]
                except (KeyError, TypeError) as exc:
                    raise LLMProviderError(
                        "Ollama no ha devuelto el contenido esperado."
                    ) from exc

                return LLMGeneration(
                    content=content,
                    model=str(data.get("model", self.settings.ollama_model)),
                    input_tokens=int(data.get("prompt_eval_count", 0) or 0),
                    output_tokens=int(data.get("eval_count", 0) or 0),
                    latency_ms=round(latency_ms, 2),
                )

        raise LLMProviderError("No se ha podido obtener respuesta de Ollama.")
