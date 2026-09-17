"""Comparación de Ollama y Groq sobre la misma incidencia."""

import asyncio

from app.core.enums import LLMProvider
from app.models.schemas import ComparisonRequest, ComparisonResponse
from app.services.triage_service import TriageService


class ComparisonService:
    """Ejecuta ambos proveedores sin duplicar los datos de la incidencia."""

    def __init__(self, triage_service: TriageService) -> None:
        self.triage_service = triage_service

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

        return ComparisonResponse(
            incident=resolved_incident,
            results=[ollama_result, groq_result],
        )
