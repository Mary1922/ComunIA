"""Test de un endpoint FastAPI con el LLM simulado."""

from fastapi.testclient import TestClient

from app.api.routes import get_triage_service
from app.main import app
from app.models.schemas import (
    ProviderMetrics,
    TriageClassification,
    TriageResponse,
)


class FakeTriageService:
    async def triage(self, request):
        return TriageResponse(
            incident=request.incident,
            classification=TriageClassification(
                category="portero_automatico",
                priority="medium",
                summary="Portero automático averiado necesita revisión técnica",
                department="mantenimiento",
                reasoning="Requiere reparación sin riesgo inmediato.",
            ),
            metrics=ProviderMetrics(
                provider=request.provider,
                model="mock-model",
                input_tokens=20,
                output_tokens=12,
                latency_ms=15,
                estimated_cost=0,
            ),
        )


def test_triage_endpoint_accepts_valid_input():
    app.dependency_overrides[get_triage_service] = (
        lambda: FakeTriageService()
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/triage",
        json={
            "incident": {
                "text": "El portero automático no funciona desde ayer.",
                "channel": "whatsapp",
                "community_reference": "Democracia 110",
                "property_reference": "2º A",
                "contact_name": "Persona de prueba",
                "contact_phone": "600123456",
            },
            "provider": "ollama",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["classification"]["priority"] == "medium"
