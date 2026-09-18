"""Tests del flujo de comparación desde el histórico de incidencias."""

from fastapi.testclient import TestClient

from app.api.routes import (
    get_comparison_repository,
    get_comparison_service,
    get_repository,
)
from app.main import app
from app.models.schemas import (
    ProviderMetrics,
    TriageClassification,
    TriageResponse,
)
from app.services.comparison_repository import ComparisonRepository
from app.services.comparison_service import ComparisonService
from app.services.incident_repository import IncidentRepository
from tests.test_comparison_service import FakeTriageService


def test_compare_historical_incident_endpoint_is_idempotent(
    tmp_path,
    sample_incident,
):
    incident_repository = IncidentRepository(tmp_path / "incidents.json")
    comparison_repository = ComparisonRepository(tmp_path / "comparisons.json")
    comparison_service = ComparisonService(
        FakeTriageService(),
        comparison_repository,
    )

    incident = incident_repository.save(
        TriageResponse(
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
    )

    app.dependency_overrides[get_repository] = lambda: incident_repository
    app.dependency_overrides[get_comparison_repository] = (
        lambda: comparison_repository
    )
    app.dependency_overrides[get_comparison_service] = (
        lambda: comparison_service
    )
    client = TestClient(app)

    first = client.post(
        f"/api/v1/incidents/{incident.incident_id}/compare"
    )
    second = client.post(
        f"/api/v1/incidents/{incident.incident_id}/compare"
    )
    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["incident_id"] == second.json()["incident_id"]
    assert first.json()["source_incident_id"] == str(incident.incident_id)
    assert len(comparison_repository.list_all()) == 1
