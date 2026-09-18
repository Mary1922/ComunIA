"""Tests del seguimiento operativo de incidencias."""

from app.core.enums import IncidentOperationalStatus
from app.models.schemas import (
    IncidentActionRequest,
    ProviderMetrics,
    TriageClassification,
    TriageResponse,
)
from app.services.incident_repository import IncidentRepository


def build_response(sample_incident) -> TriageResponse:
    return TriageResponse(
        incident=sample_incident,
        classification=TriageClassification(
            category="portero_automatico",
            priority="medium",
            summary="Portero automático averiado necesita revisión técnica",
            department="mantenimiento",
            reasoning="Observación: avería activa. Acción: revisar. Resultado: prioridad medium.",
        ),
        metrics=ProviderMetrics(
            provider="ollama",
            model="mock-model",
            input_tokens=20,
            output_tokens=10,
            latency_ms=12,
            estimated_cost=0,
        ),
    )


def test_repository_adds_operational_action_and_updates_status(
    tmp_path,
    sample_incident,
):
    repository = IncidentRepository(tmp_path / "incidents.json")
    saved = repository.save(build_response(sample_incident))

    updated = repository.add_action(
        saved.incident_id,
        IncidentActionRequest(
            action_type="provider_contact",
            description="Avisado el mantenedor y solicitada visita técnica.",
            actor="Secretaría",
            new_status="in_progress",
        ),
    )

    assert updated.operational_status == IncidentOperationalStatus.IN_PROGRESS
    assert len(updated.actions) == 1
    assert updated.actions[0].actor == "Secretaría"
    assert updated.actions[0].action_type.value == "provider_contact"


def test_old_incident_without_operational_fields_remains_compatible(
    sample_incident,
):
    raw = build_response(sample_incident).model_dump(mode="json")
    raw.pop("operational_status")
    raw.pop("actions")

    restored = TriageResponse.model_validate(raw)

    assert restored.operational_status == IncidentOperationalStatus.OPEN
    assert restored.actions == []
