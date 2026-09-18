from app.services.notification_service import build_whatsapp_demo_message


def test_build_whatsapp_demo_message_uses_reference_and_summary():
    message = build_whatsapp_demo_message(
        contact_name="Ana García",
        public_reference="Incidencia 12-2026",
        summary="Falta de señal de televisión comunitaria",
    )

    assert "Ana García" in message
    assert "Incidencia 12-2026" in message
    assert "Falta de señal de televisión comunitaria" in message
    assert "Administración de Fincas S.L." in message
    assert "gestiones pertinentes" in message
