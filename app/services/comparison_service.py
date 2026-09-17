"""Comparación de Ollama y Groq sobre la misma incidencia."""

import asyncio

from app.core.enums import LLMProvider
from app.models.schemas import ComparisonRequest, ComparisonResponse
from app.services.comparison_repository import ComparisonRepository
from app.services.triage_service import TriageService


class ComparisonService:
    """Ejecuta ambos proveedores y persiste una única comparación."""

    def __init__(
        self,
        triage_service: TriageService,
        repository: ComparisonRepository,
    ) -> None:
        self.triage_service = triage_service
        self.repository = repository

    async def compare(
        self,
        request: ComparisonRequest,
    ) -> ComparisonResponse:
        resolved_incident = self.triage_service.resolve_incident(
            request.incident
        )

        ollama_result, groq_result = await asyncio.gather(
            self.triage_service.classify_resolved_incident(
                resolved_incident,
                LLMProvider.OLLAMA,
            ),
            self.triage_service.classify_resolved_incident(
                resolved_incident,
                LLMProvider.GROQ,
            ),
        )

        response = ComparisonResponse(
            incident=resolved_incident,
            results=[ollama_result, groq_result],
        )
        return self.repository.save(response)
