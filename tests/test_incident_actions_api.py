"""Test del endpoint para registrar actuaciones operativas."""

from fastapi.testclient import TestClient

from app.api.routes import get_repository
from app.main import app
from app.models.schemas import (
    ProviderMetrics,
    TriageClassification,
    TriageResponse,
)
from app.services.incident_repository import IncidentRepository


def test_add_incident_action_endpoint(tmp_path, sample_incident):
    repository = IncidentRepository(tmp_path / "incidents.json")
    saved = repository.save(
        TriageResponse(
            incident=sample_incident,
            classification=TriageClassification(
                category="portero_automatico",
                priority="medium",
                summary="Portero automático averiado necesita revisión técnica",
                department="mantenimiento",
                reasoning="Observación: avería. Acción: reparar. Resultado: medium.",
            ),
            metrics=ProviderMetrics(
                provider="ollama",
                model="mock",
                input_tokens=1,
                output_tokens=1,
                latency_ms=1,
                estimated_cost=0,
            ),
        )
    )

    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        f"/api/v1/incidents/{saved.incident_id}/actions",
        json={
            "action_type": "appointment",
            "description": "Cita concertada para revisar la antena.",
            "actor": "Administración",
            "new_status": "scheduled",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["operational_status"] == "scheduled"
    assert payload["actions"][0]["action_type"] == "appointment"
