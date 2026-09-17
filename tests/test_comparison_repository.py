"""Tests de persistencia y evaluación humana de comparaciones."""

from app.models.schemas import (
    ComparisonResponse,
    ComparisonReviewRequest,
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
                    category="danos_agua",
                    priority="high",
                    summary="Entrada de agua activa en garaje",
                    department="mantenimiento",
                    reasoning="El agua se extiende y puede causar daños.",
                ),
                metrics=ProviderMetrics(
                    provider="ollama",
                    model="gemma3:4b",
                    input_tokens=800,
                    output_tokens=70,
                    latency_ms=15000,
                    estimated_cost=0,
                ),
            ),
            ProviderTriageResult(
                classification=TriageClassification(
                    category="garaje",
                    priority="medium",
                    summary="Humedad creciente detectada en zona de garaje",
                    department="mantenimiento",
                    reasoning="Requiere revisión técnica sin riesgo inmediato.",
                ),
                metrics=ProviderMetrics(
                    provider="groq",
                    model="qwen/qwen3.8-27b",
                    input_tokens=820,
                    output_tokens=65,
                    latency_ms=450,
                    estimated_cost=0.001,
                ),
            ),
        ],
    )


def test_comparison_is_persisted(tmp_path, sample_incident):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    comparison = build_comparison(sample_incident)

    repository.save(comparison)

    stored = repository.list_all()
    assert len(stored) == 1
    assert stored[0].incident_id == comparison.incident_id
    assert stored[0].human_review is None


def test_human_review_scores_each_provider(tmp_path, sample_incident):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    comparison = repository.save(build_comparison(sample_incident))

    updated = repository.apply_review(
        comparison.incident_id,
        ComparisonReviewRequest(
            reference_category="danos_agua",
            reference_priority="high",
            preferred_result="ollama",
            notes="Ollama coincide con la referencia humana.",
        ),
    )

    assert updated.human_review is not None
    assessments = {
        item.provider.value: item
        for item in updated.human_review.assessments
    }
    assert assessments["ollama"].exact_match is True
    assert assessments["ollama"].quality_points == 2
    assert assessments["groq"].exact_match is False
    assert assessments["groq"].quality_points == 0


def test_quality_summary_uses_only_reviewed_comparisons(
    tmp_path,
    sample_incident,
):
    repository = ComparisonRepository(tmp_path / "comparisons.json")
    reviewed = repository.save(build_comparison(sample_incident))
    repository.save(build_comparison(sample_incident))

    repository.apply_review(
        reviewed.incident_id,
        ComparisonReviewRequest(
            reference_category="danos_agua",
            reference_priority="high",
            preferred_result="ollama",
        ),
    )

    summary = repository.quality_summary()
    providers = {item.provider.value: item for item in summary.providers}

    assert summary.total_comparisons == 2
    assert summary.reviewed_comparisons == 1
    assert providers["ollama"].comparisons == 2
    assert providers["ollama"].reviewed == 1
    assert providers["ollama"].category_accuracy_pct == 100.0
    assert providers["ollama"].priority_accuracy_pct == 100.0
    assert providers["ollama"].exact_match_rate_pct == 100.0
    assert providers["ollama"].preferred_count == 1
    assert providers["groq"].exact_match_rate_pct == 0.0
