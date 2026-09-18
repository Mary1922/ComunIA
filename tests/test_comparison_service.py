"""Test de que /compare persiste un único registro comparativo."""

import pytest

from app.models.schemas import (
    ComparisonRequest,
    ProviderMetrics,
    ProviderTriageResult,
    TriageClassification,
    TriageResponse,
)
from app.services.comparison_repository import ComparisonRepository
from app.services.comparison_service import ComparisonService


class FakeTriageService:
    def resolve_incident(self, incident):
        return incident

    async def classify_resolved_incident(self, incident, provider_name):
        return ProviderTriageResult(
            classification=TriageClassification(
                category="portero_automatico",
                priority="medium",
                summary="Portero automático averiado necesita revisión técnica",
                department="mantenimiento",
                reasoning="Requiere reparación sin riesgo inmediato.",
            ),
            metrics=ProviderMetrics(
                provider=provider_name,
                model=f"mock-{provider_name.value}",
                input_tokens=10,
                output_tokens=10,
                latency_ms=10,
                estimated_cost=0,
            ),
        )


@pytest.mark.asyncio
async def test_compare_persists_both_provider_results(tmp_path, sample_incident):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    service = ComparisonService(FakeTriageService(), repository)

    response = await service.compare(
        ComparisonRequest(incident=sample_incident)
    )

    stored = repository.list_all()
    assert len(stored) == 1
    assert stored[0].incident_id == response.incident_id
    assert {item.metrics.provider.value for item in stored[0].results} == {
        "ollama",
        "groq",
    }


@pytest.mark.asyncio
async def test_compare_existing_incident_is_idempotent(
    tmp_path,
    sample_incident,
):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    service = ComparisonService(FakeTriageService(), repository)
    incident = TriageResponse(
        incident=sample_incident,
        classification=TriageClassification(
            category="portero_automatico",
            priority="medium",
            summary="Portero automático averiado necesita revisión técnica",
            department="mantenimiento",
            reasoning="Requiere reparación sin riesgo inmediato.",
        ),
        metrics=ProviderMetrics(
            provider="ollama",
            model="gemma3:4b",
            input_tokens=10,
            output_tokens=10,
            latency_ms=100,
            estimated_cost=0,
        ),
    )

    first = await service.compare_existing_incident(incident)
    second = await service.compare_existing_incident(incident)

    stored = repository.list_all()
    assert len(stored) == 1
    assert first.incident_id == second.incident_id
    assert first.source_incident_id == incident.incident_id
    assert stored[0].source_incident_id == incident.incident_id
