"""Conversión y validación de la respuesta textual del LLM."""

import json

from pydantic import ValidationError

from app.core.exceptions import InvalidLLMResponseError
from app.models.schemas import TriageClassification


def _strip_code_fence(value: str) -> str:
    """Tolera bloques ```json ... ``` sin aceptar prosa adicional."""

    text = value.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()

    return text


def parse_triage_response(raw_response: str) -> TriageClassification:
    """Convierte JSON a TriageClassification o produce un error controlado."""

    clean_response = _strip_code_fence(raw_response)

    try:
        data = json.loads(clean_response)
    except json.JSONDecodeError as exc:
        raise InvalidLLMResponseError(
            "La respuesta del LLM no es JSON válido."
        ) from exc

    try:
        return TriageClassification.model_validate(data)
    except ValidationError as exc:
        raise InvalidLLMResponseError(
            f"La respuesta del LLM no cumple el esquema: {exc}"
        ) from exc
