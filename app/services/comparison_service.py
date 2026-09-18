"""Comparación de Ollama y Groq sobre la misma incidencia."""

import asyncio
from uuid import UUID

from app.core.enums import LLMProvider
from app.models.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    IncidentRequest,
    TriageResponse,
)
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

    async def _compare_incident(
        self,
        incident: IncidentRequest,
        *,
        source_incident_id: UUID | None = None,
    ) -> ComparisonResponse:
        resolved_incident = self.triage_service.resolve_incident(incident)

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
            source_incident_id=source_incident_id,
            incident=resolved_incident,
            results=[ollama_result, groq_result],
        )
        return self.repository.save(response)

    async def compare(
        self,
        request: ComparisonRequest,
    ) -> ComparisonResponse:
        return await self._compare_incident(request.incident)

    async def compare_existing_incident(
        self,
        incident: TriageResponse,
    ) -> ComparisonResponse:
        """Compara una incidencia del histórico evitando duplicados."""

        existing = self.repository.find_by_source_incident_id(
            incident.incident_id
        )
        if existing is not None:
            return existing

        return await self._compare_incident(
            incident.incident,
            source_incident_id=incident.incident_id,
        )
