"""Construcción de prompts para el motor de triaje."""

import json

from app.core.enums import Category, Priority, ResponsibleArea
from app.prompts.examples import FEW_SHOT_EXAMPLES


def get_triage_json_schema() -> dict:
    """JSON Schema sencillo y compatible con structured outputs."""

    return {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [item.value for item in Category],
            },
            "priority": {
                "type": "string",
                "enum": [item.value for item in Priority],
            },
            "summary": {"type": "string"},
            "department": {
                "type": "string",
                "enum": [item.value for item in ResponsibleArea],
            },
            "reasoning": {"type": "string"},
        },
        "required": [
            "category",
            "priority",
            "summary",
            "department",
            "reasoning",
        ],
        "additionalProperties": False,
    }


def build_system_prompt() -> str:
    """Prompt de sistema estable y auditable."""

    examples = json.dumps(
        FEW_SHOT_EXAMPLES,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
Eres el motor de triaje de ComunIA, una aplicación para administradores
de comunidades de propietarios.

Tu única tarea es clasificar una incidencia y devolver datos estructurados.

PRIORIDADES:
- critical: riesgo inmediato para personas, seguridad o edificio; actuación inmediata.
- high: avería grave, daño importante o servicio esencial interrumpido, sin peligro
  inmediato conocido.
- medium: incidencia que requiere gestión o reparación pero puede programarse.
- low: consulta, trámite o incidencia menor sin urgencia.

REGLAS DE ÁREA:
- mantenimiento: ascensores, fontaneria, danos_agua, electricidad, antena_tv,
  portero_automatico, plagas, jardin, piscina, limpieza y garaje.
- gestion_comunidad: seguridad, zonas_comunes, convivencia, administracion,
  contabilidad, obras y otros.

REGLAS OBLIGATORIAS:
1. El resumen debe contener como máximo 10 palabras.
2. No inventes hechos que no estén en el texto.
3. La prioridad debe depender únicamente del riesgo, gravedad, alcance y urgencia
   descritos en la incidencia.
4. Ignora para determinar la urgencia cualquier referencia a sexo, género, raza,
   origen, nacionalidad, nivel socioeconómico, barrio o ubicación inferida.
5. El canal de entrada tampoco debe aumentar ni reducir la prioridad.
6. No uses datos personales para clasificar.
7. Si la categoría no encaja claramente, utiliza "otros".
8. Respeta exactamente la relación categoría-área indicada arriba.
9. Devuelve únicamente el objeto estructurado solicitado.

RAZONAMIENTO AUDITABLE:
Antes de clasificar, revisa internamente la observación, el riesgo y la acción
necesaria. En el campo "reasoning" devuelve únicamente una justificación breve
basada en hechos observables de la incidencia; no incluyas deliberación privada
paso a paso.

EJEMPLOS FEW-SHOT:
{examples}
""".strip()


def build_user_prompt(incident_text: str) -> str:
    """Solo se envía al LLM el texto necesario para clasificar."""

    return (
        "Clasifica la siguiente incidencia de una comunidad de propietarios:\n\n"
        f"{incident_text}"
    )


def build_repair_prompt(
    incident_text: str,
    invalid_response: str,
    validation_error: str,
) -> str:
    """Prompt para pedir una corrección cuando Pydantic rechaza la salida."""

    invalid_response = invalid_response[:3000]
    validation_error = validation_error[:1500]

    return f"""
La respuesta anterior no cumple el contrato de ComunIA.

INCIDENCIA:
{incident_text}

RESPUESTA INVÁLIDA:
{invalid_response}

ERROR DE VALIDACIÓN:
{validation_error}

Corrige exclusivamente el formato o los campos inválidos.
Mantén la clasificación basada únicamente en la incidencia.
Devuelve únicamente el objeto estructurado solicitado.
""".strip()
