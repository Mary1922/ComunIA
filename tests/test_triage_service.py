"""Tests del servicio de triaje usando un LLM simulado."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.enums import LLMProvider
from app.llm.base import BaseLLMProvider, LLMGeneration
from app.models.schemas import TriageRequest
from app.services.community_service import CommunityService
from app.services.incident_repository import IncidentRepository
from app.services.triage_service import TriageService


class RepairingFakeProvider(BaseLLMProvider):
    provider = LLMProvider.OLLAMA

    def __init__(self):
        self.calls = 0

    async def generate(self, system_prompt, user_prompt, json_schema):
        self.calls += 1

        if self.calls == 1:
            content = '{"priority": 123}'
        else:
            content = """
            {
              "category": "portero_automatico",
              "priority": "medium",
              "summary": "Portero automático averiado necesita revisión técnica",
              "department": "mantenimiento",
              "reasoning": "Requiere reparación sin riesgo inmediato descrito."
            }
            """

        return LLMGeneration(
            content=content,
            model="fake-model",
            input_tokens=10,
            output_tokens=10,
            latency_ms=5.0,
        )


@pytest.mark.asyncio
async def test_service_repairs_invalid_llm_response(
    tmp_path,
    sample_incident,
):
    communities = tmp_path / "communities.json"
    communities.write_text(
        """[
          {
            "id": "COM-1",
            "name": "Avenida de la Democracia 110"
          }
        ]""",
        encoding="utf-8",
    )

    repository = IncidentRepository(tmp_path / "incidents.json")
    fake_provider = RepairingFakeProvider()

    settings = Settings(
        communities_path=communities,
        incidents_path=tmp_path / "incidents.json",
        max_repair_attempts=1,
    )

    service = TriageService(
        settings=settings,
        community_service=CommunityService(communities),
        repository=repository,
        provider_factory=lambda provider: fake_provider,
    )

    response = await service.triage(
        TriageRequest(
            incident=sample_incident,
            provider="ollama",
        )
    )

    assert fake_provider.calls == 2
    assert response.classification.priority.value == "medium"
    assert response.metrics.input_tokens == 20
    assert response.metrics.output_tokens == 20
