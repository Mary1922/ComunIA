"""Orquestación principal del triaje."""

from collections.abc import Callable

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.core.exceptions import InvalidLLMResponseError
from app.guardrails.priority_guardrail import apply_priority_guardrail
from app.llm.base import BaseLLMProvider
from app.llm.factory import create_provider
from app.models.schemas import (
    IncidentRequest,
    ProviderTriageResult,
    TriageRequest,
    TriageResponse,
)
from app.parsers.response_parser import parse_triage_response
from app.prompts.triage_prompt import (
    build_repair_prompt,
    build_system_prompt,
    build_user_prompt,
    get_triage_json_schema,
)
from app.services.community_service import CommunityService
from app.services.incident_repository import IncidentRepository
from app.services.metrics_service import MetricsService


ProviderFactory = Callable[[LLMProvider], BaseLLMProvider]


class TriageService:
    """Coordina validación, comunidad, LLM, reparación y métricas."""

    def __init__(
        self,
        settings: Settings,
        community_service: CommunityService,
        repository: IncidentRepository,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.settings = settings
        self.community_service = community_service
        self.repository = repository
        self.metrics_service = MetricsService(settings)
        self.provider_factory = provider_factory or (
            lambda provider: create_provider(provider, settings)
        )

    def resolve_incident(
        self,
        incident: IncidentRequest,
    ) -> IncidentRequest:
        """Valida la comunidad y sustituye el texto por su nombre canónico."""

        match = self.community_service.match(
            incident.community_reference
        )

        return incident.model_copy(
            update={"community_reference": match.canonical_name}
        )

    async def classify_resolved_incident(
        self,
        incident: IncidentRequest,
        provider_name: LLMProvider,
    ) -> ProviderTriageResult:
        """Clasifica una incidencia cuya comunidad ya ha sido validada."""

        provider = self.provider_factory(provider_name)
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(incident.text)
        schema = get_triage_json_schema()

        total_input_tokens = 0
        total_output_tokens = 0
        total_latency_ms = 0.0
        last_model = "unknown"
        last_invalid_response = ""
        last_error = ""

        attempts = self.settings.max_repair_attempts + 1

        for attempt_index in range(attempts):
            generation = await provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=schema,
            )

            total_input_tokens += generation.input_tokens
            total_output_tokens += generation.output_tokens
            total_latency_ms += generation.latency_ms
            last_model = generation.model

            try:
                classification = parse_triage_response(
                    generation.content
                )
            except InvalidLLMResponseError as exc:
                last_invalid_response = generation.content
                last_error = str(exc)

                if attempt_index >= attempts - 1:
                    raise

                user_prompt = build_repair_prompt(
                    incident_text=incident.text,
                    invalid_response=last_invalid_response,
                    validation_error=last_error,
                )
                continue

            classification = apply_priority_guardrail(
                incident.text,
                classification,
            )

            metrics = self.metrics_service.build_metrics(
                provider=provider_name,
                model=last_model,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                latency_ms=total_latency_ms,
            )

            return ProviderTriageResult(
                classification=classification,
                metrics=metrics,
            )

        raise InvalidLLMResponseError(
            "El modelo no ha podido producir una respuesta válida."
        )

    async def triage(self, request: TriageRequest) -> TriageResponse:
        """Procesa y persiste una incidencia con un proveedor."""

        resolved_incident = self.resolve_incident(request.incident)

        result = await self.classify_resolved_incident(
            resolved_incident,
            request.provider,
        )

        response = TriageResponse(
            incident=resolved_incident,
            classification=result.classification,
            metrics=result.metrics,
        )

        return self.repository.save(response)
