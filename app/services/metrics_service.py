"""Cálculo de métricas técnicas y coste estimado."""

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.models.schemas import ProviderMetrics


class MetricsService:
    """Construye métricas comparables para cualquier proveedor."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def estimate_cost(
        self,
        provider: LLMProvider,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        if provider == LLMProvider.OLLAMA:
            return 0.0

        input_cost = (
            input_tokens / 1_000_000
        ) * self.settings.groq_input_cost_per_1m
        output_cost = (
            output_tokens / 1_000_000
        ) * self.settings.groq_output_cost_per_1m

        return round(input_cost + output_cost, 8)

    def build_metrics(
        self,
        provider: LLMProvider,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ) -> ProviderMetrics:
        return ProviderMetrics(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost=self.estimate_cost(
                provider,
                input_tokens,
                output_tokens,
            ),
        )
