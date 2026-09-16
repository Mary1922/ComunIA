"""Factoría de proveedores LLM."""

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.llm.base import BaseLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def create_provider(
    provider: LLMProvider,
    settings: Settings,
) -> BaseLLMProvider:
    """Crea el cliente adecuado sin acoplar el servicio de triaje."""

    if provider == LLMProvider.OLLAMA:
        return OllamaProvider(settings)

    if provider == LLMProvider.OPENAI:
        return OpenAIProvider(settings)

    raise ValueError(f"Proveedor no soportado: {provider}")
