"""Guardrail mínimo para riesgos críticos explícitos."""

import re
import unicodedata

from app.core.enums import Priority
from app.models.schemas import TriageClassification


CRITICAL_PATTERNS = [
    r"persona\s+atrapad",
    r"atrapad[oa]\s+en\s+el\s+ascensor",
    r"incendio",
    r"fuego\s+activo",
    r"olor\s+(fuerte\s+)?a\s+gas",
    r"fuga\s+de\s+gas",
    r"electrocuci",
]


def _normalize(value: str) -> str:
    value = value.lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in value if not unicodedata.combining(char)
    )


def apply_priority_guardrail(
    incident_text: str,
    classification: TriageClassification,
) -> TriageClassification:
    """Eleva a critical cuando existe un indicador crítico inequívoco.

    El guardrail nunca reduce la prioridad propuesta por el LLM.
    """

    normalized = _normalize(incident_text)

    matched = any(
        re.search(pattern, normalized)
        for pattern in CRITICAL_PATTERNS
    )

    if not matched or classification.priority == Priority.CRITICAL:
        return classification

    note = (
        " Guardrail aplicado: el texto contiene un indicador explícito "
        "de riesgo crítico."
    )

    return classification.model_copy(
        update={
            "priority": Priority.CRITICAL,
            "reasoning": (classification.reasoning + note)[:1000],
        }
    )
