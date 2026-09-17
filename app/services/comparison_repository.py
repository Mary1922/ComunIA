"""Persistencia y evaluación humana de comparaciones entre proveedores."""

import json
from pathlib import Path
from threading import Lock
from uuid import UUID

from app.core.enums import LLMProvider
from app.core.exceptions import ComparisonNotFoundError, PersistenceError
from app.models.schemas import (
    ComparisonHumanReview,
    ComparisonQualitySummary,
    ComparisonResponse,
    ComparisonReviewRequest,
    ProviderQualityAssessment,
    ProviderQualitySummary,
)


class ComparisonRepository:
    """Repositorio JSON de comparaciones y métricas de calidad validadas."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.write_text("[]\n", encoding="utf-8")

    def _read_raw(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(
                "No se ha podido leer data/comparisons.json."
            ) from exc

        if not isinstance(data, list):
            raise PersistenceError(
                "data/comparisons.json debe contener una lista."
            )
        return data

    def _write_raw(self, data: list[dict]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self.path)
        except OSError as exc:
            raise PersistenceError(
                "No se ha podido guardar data/comparisons.json."
            ) from exc

    def save(self, response: ComparisonResponse) -> ComparisonResponse:
        """Guarda una comparación pendiente de validación humana."""

        with self._lock:
            data = self._read_raw()
            data.append(response.model_dump(mode="json"))
            self._write_raw(data)
        return response

    def list_all(self) -> list[ComparisonResponse]:
        """Devuelve el histórico completo de comparaciones."""

        with self._lock:
            data = self._read_raw()

        try:
            return [ComparisonResponse.model_validate(item) for item in data]
        except Exception as exc:
            raise PersistenceError(
                "Existe una comparación almacenada con formato inválido."
            ) from exc

    @staticmethod
    def _assessment_for(
        response: ComparisonResponse,
        review: ComparisonReviewRequest,
    ) -> list[ProviderQualityAssessment]:
        assessments: list[ProviderQualityAssessment] = []

        for result in response.results:
            category_correct = (
                result.classification.category == review.reference_category
            )
            priority_correct = (
                result.classification.priority == review.reference_priority
            )
            assessments.append(
                ProviderQualityAssessment(
                    provider=result.metrics.provider,
                    category_correct=category_correct,
                    priority_correct=priority_correct,
                    exact_match=category_correct and priority_correct,
                    quality_points=int(category_correct) + int(priority_correct),
                )
            )

        return assessments

    def apply_review(
        self,
        comparison_id: UUID,
        review: ComparisonReviewRequest,
    ) -> ComparisonResponse:
        """Guarda la referencia humana y calcula aciertos de cada modelo."""

        with self._lock:
            data = self._read_raw()

            for index, item in enumerate(data):
                if item.get("incident_id") != str(comparison_id):
                    continue

                current = ComparisonResponse.model_validate(item)
                human_review = ComparisonHumanReview(
                    reference_category=review.reference_category,
                    reference_priority=review.reference_priority,
                    preferred_result=review.preferred_result,
                    notes=review.notes,
                    assessments=self._assessment_for(current, review),
                )
                updated = current.model_copy(
                    update={"human_review": human_review}
                )
                data[index] = updated.model_dump(mode="json")
                self._write_raw(data)
                return updated

        raise ComparisonNotFoundError(
            f"No existe la comparación {comparison_id}."
        )

    def quality_summary(self) -> ComparisonQualitySummary:
        """Calcula calidad frente a referencia humana y métricas operativas."""

        comparisons = self.list_all()
        stats = {
            provider: {
                "comparisons": 0,
                "reviewed": 0,
                "category_correct": 0,
                "priority_correct": 0,
                "exact_match": 0,
                "preferred_count": 0,
                "latency_total": 0.0,
                "cost_total": 0.0,
            }
            for provider in (LLMProvider.OLLAMA, LLMProvider.GROQ)
        }

        reviewed_comparisons = 0

        for comparison in comparisons:
            review = comparison.human_review
            if review is not None:
                reviewed_comparisons += 1

            for result in comparison.results:
                provider = result.metrics.provider
                provider_stats = stats[provider]
                provider_stats["comparisons"] += 1
                provider_stats["latency_total"] += result.metrics.latency_ms
                provider_stats["cost_total"] += result.metrics.estimated_cost

                if review is None:
                    continue

                assessment = next(
                    item
                    for item in review.assessments
                    if item.provider == provider
                )
                provider_stats["reviewed"] += 1
                provider_stats["category_correct"] += int(
                    assessment.category_correct
                )
                provider_stats["priority_correct"] += int(
                    assessment.priority_correct
                )
                provider_stats["exact_match"] += int(
                    assessment.exact_match
                )
                provider_stats["preferred_count"] += int(
                    review.preferred_result.value == provider.value
                )

        provider_summaries: list[ProviderQualitySummary] = []
        for provider in (LLMProvider.OLLAMA, LLMProvider.GROQ):
            item = stats[provider]
            comparisons_count = item["comparisons"]
            reviewed_count = item["reviewed"]

            def percentage(key: str) -> float | None:
                if reviewed_count == 0:
                    return None
                return round(item[key] / reviewed_count * 100, 1)

            provider_summaries.append(
                ProviderQualitySummary(
                    provider=provider,
                    comparisons=comparisons_count,
                    reviewed=reviewed_count,
                    category_accuracy_pct=percentage("category_correct"),
                    priority_accuracy_pct=percentage("priority_correct"),
                    exact_match_rate_pct=percentage("exact_match"),
                    preferred_count=item["preferred_count"],
                    average_latency_ms=(
                        round(
                            item["latency_total"] / comparisons_count,
                            2,
                        )
                        if comparisons_count
                        else None
                    ),
                    total_estimated_cost=round(item["cost_total"], 10),
                )
            )

        return ComparisonQualitySummary(
            total_comparisons=len(comparisons),
            reviewed_comparisons=reviewed_comparisons,
            providers=provider_summaries,
        )
