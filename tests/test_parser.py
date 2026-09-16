"""Tests del parser type-safe."""

import pytest

from app.core.exceptions import InvalidLLMResponseError
from app.parsers.response_parser import parse_triage_response


def test_parser_accepts_valid_json():
    raw = """
    {
      "category": "portero_automatico",
      "priority": "medium",
      "summary": "Portero automático averiado necesita revisión técnica",
      "department": "mantenimiento",
      "reasoning": "La avería requiere reparación pero no es crítica."
    }
    """

    result = parse_triage_response(raw)
    assert result.category.value == "portero_automatico"


def test_parser_rejects_structural_hallucination():
    raw = """
    {
      "categoria_inventada": "ascensor",
      "urgencia": 99
    }
    """

    with pytest.raises(InvalidLLMResponseError):
        parse_triage_response(raw)
