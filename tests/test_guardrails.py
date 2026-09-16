"""Tests del guardrail de prioridad."""

from app.guardrails.priority_guardrail import apply_priority_guardrail
from app.models.schemas import TriageClassification


def test_trapped_person_is_forced_to_critical():
    initial = TriageClassification(
        category="ascensores",
        priority="medium",
        summary="Persona atrapada dentro del ascensor comunitario",
        department="mantenimiento",
        reasoning="El ascensor presenta una avería.",
    )

    result = apply_priority_guardrail(
        "Hay una persona atrapada dentro del ascensor.",
        initial,
    )

    assert result.priority.value == "critical"
