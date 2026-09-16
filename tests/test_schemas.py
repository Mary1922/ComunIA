"""Tests del contrato Pydantic."""

import pytest
from pydantic import ValidationError

from app.models.schemas import TriageClassification


def test_summary_with_ten_or_fewer_words_is_valid():
    result = TriageClassification(
        category="contabilidad",
        priority="low",
        summary="Solicitud de copia del último recibo comunitario",
        department="gestion_comunidad",
        reasoning="Es una solicitud documental sin urgencia.",
    )

    assert result.priority.value == "low"


def test_summary_over_ten_words_is_rejected():
    with pytest.raises(ValidationError):
        TriageClassification(
            category="contabilidad",
            priority="low",
            summary=(
                "El propietario solicita una copia completa del último "
                "recibo emitido por la comunidad"
            ),
            department="gestion_comunidad",
            reasoning="Es una solicitud documental sin urgencia.",
        )


def test_category_must_match_responsible_area():
    with pytest.raises(ValidationError):
        TriageClassification(
            category="seguridad",
            priority="high",
            summary="Problema de seguridad comunicado por un propietario",
            department="mantenimiento",
            reasoning="Requiere gestión de la comunidad.",
        )
