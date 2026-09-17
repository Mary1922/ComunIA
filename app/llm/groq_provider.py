"""Proveedor externo Groq mediante API compatible con OpenAI Chat Completions."""

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


class GroqProvider(BaseLLMProvider):
    """Cliente HTTP de Groq con Structured Outputs mediante JSON Schema."""

    provider = LLMProvider.GROQ

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extrae el contenido JSON de la primera respuesta del modelo."""

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                "Groq no ha devuelto el contenido esperado."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError(
                "Groq ha devuelto una respuesta vacía."
            )

        return content

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> LLMGeneration:
        if self.settings.groq_api_key is None:
            raise LLMConfigurationError(
                "Falta GROQ_API_KEY en el archivo .env."
            )

        url = f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": (
                f"Bearer {self.settings.groq_api_key.get_secret_value()}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "reasoning_effort": "none",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "comunia_triage",
                    "strict": True,
                    "schema": json_schema,
                },
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
                        "Error temporal de conexión con Groq."
                    )
                    if attempt == self.settings.max_retries:
                        raise error from exc
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                latency_ms = (time.perf_counter() - started) * 1000

                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after")
                    error = LLMRateLimitError(
                        "Groq ha aplicado un rate limit."
                    )
                    if attempt == self.settings.max_retries:
                        raise error

                    try:
                        delay = float(retry_after) if retry_after else None
                    except ValueError:
                        delay = None

                    await asyncio.sleep(
                        delay if delay is not None else min(2 ** (attempt - 1), 8)
                    )
                    continue

                if response.status_code >= 500:
                    error = LLMTransientError(
                        f"Groq ha devuelto {response.status_code}."
                    )
                    if attempt == self.settings.max_retries:
                        raise error
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue

                if response.status_code >= 400:
                    detail = response.text[:1000]
                    raise LLMProviderError(
                        "Groq ha rechazado la petición "
                        f"({response.status_code}): {detail}"
                    )

                data = response.json()
                content = self._extract_content(data)
                usage = data.get("usage") or {}

                return LLMGeneration(
                    content=content,
                    model=str(data.get("model", self.settings.groq_model)),
                    input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                    output_tokens=int(
                        usage.get("completion_tokens", 0) or 0
                    ),
                    latency_ms=round(latency_ms, 2),
                )

        raise LLMProviderError("No se ha podido obtener respuesta de Groq.")
