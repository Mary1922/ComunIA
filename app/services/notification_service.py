"""Mensajería saliente de ComunIA.

La versión actual implementa únicamente una previsualización segura para demos.
No realiza peticiones a WhatsApp ni a ningún proveedor externo.
"""


def build_whatsapp_demo_message(
    *,
    contact_name: str,
    public_reference: str,
    summary: str,
) -> str:
    """Construye el texto que podría enviarse por WhatsApp en una fase futura."""

    name = contact_name.strip() or "vecino/a"
    reference = public_reference.strip() or "la incidencia registrada"
    clean_summary = summary.strip() or "la incidencia comunicada"

    return (
        f"Hola, {name}.\n\n"
        "Administración de Fincas S.L. ha procesado su consulta "
        f"({reference}) de \"{clean_summary}\" y va a realizar las gestiones "
        "pertinentes.\n\n"
        "Gracias por ponerse en contacto con nosotros."
    )
