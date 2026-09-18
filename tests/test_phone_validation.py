import pytest
from pydantic import ValidationError

from app.models.schemas import IncidentRequest


def make_incident(phone: str) -> IncidentRequest:
    return IncidentRequest(
        text="El portero automático no funciona.",
        channel="phone",
        community_reference="Avenida Pablo Neruda 11",
        property_reference="Portal 1 · 2º B",
        contact_name="Persona de prueba",
        contact_phone=phone,
    )


def test_spanish_phone_accepts_exactly_nine_digits():
    incident = make_incident("600123456")
    assert incident.contact_phone == "600123456"


@pytest.mark.parametrize("phone", ["60012345", "6001234567", "+34600123456", "60012A456"])
def test_spanish_phone_rejects_invalid_formats(phone: str):
    with pytest.raises(ValidationError):
        make_incident(phone)
