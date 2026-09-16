"""Fixtures compartidas de Pytest."""

import pytest

from app.models.schemas import IncidentRequest


@pytest.fixture
def sample_incident() -> IncidentRequest:
    return IncidentRequest(
        text="El portero automático no funciona desde ayer.",
        channel="whatsapp",
        community_reference="Avenida de la Democracia 110",
        property_reference="Portal 1 - 2º A",
        contact_name="Persona de prueba",
        contact_phone="600123456",
    )
