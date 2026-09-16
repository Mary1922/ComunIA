"""Contrato común de los proveedores LLM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.enums import LLMProvider


@dataclass(slots=True)
class LLMGeneration:
    """Respuesta técnica normalizada de cualquier proveedor."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class BaseLLMProvider(ABC):
    """Interfaz que deben cumplir todos los proveedores."""

    provider: LLMProvider

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict,
    ) -> LLMGeneration:
        """Genera una respuesta estructurada."""
        raise NotImplementedError
