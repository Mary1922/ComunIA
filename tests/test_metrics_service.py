"""Tests de coste estimado de proveedores."""

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.services.metrics_service import MetricsService


def test_ollama_estimated_cost_is_zero():
    service = MetricsService(Settings())
    assert service.estimate_cost(LLMProvider.OLLAMA, 1000, 1000) == 0.0


def test_groq_estimated_cost_uses_reference_rates():
    service = MetricsService(
        Settings(
            groq_input_cost_per_1m=0.80,
            groq_output_cost_per_1m=4.00,
        )
    )

    cost = service.estimate_cost(
        LLMProvider.GROQ,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )

    assert cost == 4.8
