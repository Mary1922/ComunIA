"""Tests de endpoints de revisión y calidad de comparaciones."""

from fastapi.testclient import TestClient

from app.api.routes import get_comparison_repository
from app.main import app
from app.models.schemas import (
    ComparisonResponse,
    ProviderMetrics,
    ProviderTriageResult,
    TriageClassification,
)
from app.services.comparison_repository import ComparisonRepository


def build_comparison(sample_incident) -> ComparisonResponse:
    return ComparisonResponse(
        incident=sample_incident,
        results=[
            ProviderTriageResult(
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
                    input_tokens=20,
                    output_tokens=12,
                    latency_ms=1000,
                    estimated_cost=0,
                ),
            ),
            ProviderTriageResult(
                classification=TriageClassification(
                    category="portero_automatico",
                    priority="medium",
                    summary="Portero automático sin servicio desde ayer",
                    department="mantenimiento",
                    reasoning="La avería no implica riesgo inmediato.",
                ),
                metrics=ProviderMetrics(
                    provider="groq",
                    model="qwen/qwen3.8-27b",
                    input_tokens=21,
                    output_tokens=11,
                    latency_ms=300,
                    estimated_cost=0.0001,
                ),
            ),
        ],
    )


def test_comparison_review_endpoint_and_quality(tmp_path, sample_incident):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    comparison = repository.save(build_comparison(sample_incident))

    app.dependency_overrides[get_comparison_repository] = lambda: repository
    client = TestClient(app)

    response = client.patch(
        f"/api/v1/comparisons/{comparison.incident_id}/review",
        json={
            "reference_category": "portero_automatico",
            "reference_priority": "medium",
            "preferred_result": "tie",
            "notes": "Ambos clasifican correctamente.",
        },
    )

    assert response.status_code == 200
    assert response.json()["human_review"] is not None
    assert all(
        item["exact_match"]
        for item in response.json()["human_review"]["assessments"]
    )

    quality = client.get("/api/v1/comparisons/quality")
    app.dependency_overrides.clear()

    assert quality.status_code == 200
    assert quality.json()["reviewed_comparisons"] == 1
    assert all(
        item["exact_match_rate_pct"] == 100.0
        for item in quality.json()["providers"]
    )
