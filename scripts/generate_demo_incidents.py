"""Genera incidencias sintéticas para demos de ComunIA sin llamar a ningún LLM.

Uso habitual:
    python scripts/generate_demo_incidents.py --count 50

El script añade registros a data/incidents.json, conserva los existentes y evita
crear duplicados si se ejecuta de nuevo con la misma semilla.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import sys
from uuid import NAMESPACE_URL, uuid5

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.enums import (  # noqa: E402
    Channel,
    HumanReviewStatus,
    IncidentActionType,
    IncidentOperationalStatus,
    LLMProvider,
    Priority,
)
from app.models.schemas import (  # noqa: E402
    CATEGORY_AREA_MAP,
    IncidentAction,
    IncidentRequest,
    ProviderMetrics,
    TriageClassification,
    TriageResponse,
)


FIRST_NAMES = [
    "Lucía", "Carlos", "Marta", "Javier", "Elena", "Daniel", "Sofía",
    "Álvaro", "Patricia", "Raúl", "Isabel", "Miguel", "Nuria", "David",
    "Beatriz", "Sergio", "Ana", "Héctor", "Cristina", "Pablo",
]
LAST_NAMES = [
    "Martín", "Sanz", "Romero", "Navarro", "Ortega", "Iglesias", "Vega",
    "Molina", "Serrano", "Crespo", "Prieto", "Ramos", "Gil", "Blanco",
    "Fuentes", "Méndez", "Rey", "Campos", "Pastor", "Lorenzo",
]
LETTERS = ["A", "B", "C", "D"]

# category, priority, description, summary, observation
CASES = [
    ("ascensores", "critical", "Hay una persona atrapada en el ascensor y las puertas no se abren.", "Persona atrapada en ascensor, requiere actuación inmediata", "hay una persona atrapada en el ascensor"),
    ("ascensores", "high", "El ascensor está parado entre plantas y no responde a las llamadas.", "Ascensor detenido entre plantas sin respuesta", "el ascensor está inmovilizado entre plantas"),
    ("fontaneria", "high", "Una tubería comunitaria pierde agua de forma continua en el cuarto de contadores.", "Fuga activa en tubería del cuarto de contadores", "existe una fuga activa en una tubería comunitaria"),
    ("danos_agua", "high", "Está entrando agua por el techo del garaje y la mancha sigue aumentando.", "Entrada de agua activa en techo del garaje", "la entrada de agua continúa y aumenta"),
    ("electricidad", "critical", "Huele a quemado en el cuadro eléctrico comunitario y se observan chispas.", "Chispas y olor a quemado en cuadro eléctrico", "hay chispas y olor a quemado en el cuadro"),
    ("electricidad", "high", "La iluminación de todos los rellanos se ha quedado sin suministro.", "Rellanos comunitarios sin iluminación eléctrica", "la iluminación comunitaria está totalmente interrumpida"),
    ("antena_tv", "medium", "Desde esta mañana ninguna vivienda recibe señal de televisión comunitaria.", "Comunidad sin señal de televisión desde esta mañana", "la señal de televisión comunitaria está interrumpida"),
    ("portero_automatico", "medium", "El portero automático no abre la puerta y no se escucha desde las viviendas.", "Portero automático sin audio ni apertura", "el portero automático ha perdido audio y apertura"),
    ("plagas", "medium", "Se han visto cucarachas en el cuarto de basuras y en el portal.", "Presencia de cucarachas en zonas comunes", "se observan cucarachas en varias zonas comunes"),
    ("jardin", "low", "El riego automático del jardín no funciona en una de las zonas.", "Riego automático averiado en zona del jardín", "una zona del jardín no recibe riego"),
    ("piscina", "medium", "La depuradora de la piscina hace un ruido anormal y ha dejado de filtrar.", "Depuradora de piscina sin filtración correcta", "la depuradora ha dejado de filtrar"),
    ("seguridad", "high", "La puerta principal no cierra y queda abierta aunque nadie la esté usando.", "Puerta principal queda abierta y no cierra", "la puerta principal no puede asegurarse"),
    ("limpieza", "low", "La limpieza del portal de esta semana no se ha realizado.", "Limpieza semanal del portal no realizada", "el servicio de limpieza previsto no se ha realizado"),
    ("zonas_comunes", "medium", "Una baldosa del portal está levantada y puede provocar tropiezos.", "Baldosa levantada con riesgo de tropiezo", "hay una baldosa levantada en una zona de paso"),
    ("garaje", "medium", "La puerta del garaje abre pero no vuelve a cerrar automáticamente.", "Puerta de garaje no cierra automáticamente", "la puerta del garaje queda abierta tras el acceso"),
    ("convivencia", "low", "Un vecino comunica ruidos reiterados durante la madrugada.", "Queja por ruidos reiterados durante la madrugada", "se comunican molestias reiteradas por ruido nocturno"),
    ("administracion", "low", "Se solicita una copia del último acta de la junta de propietarios.", "Solicitud de copia del último acta comunitaria", "se solicita documentación administrativa de la comunidad"),
    ("contabilidad", "low", "Un propietario pide aclaración sobre un recibo extraordinario cargado este mes.", "Consulta sobre recibo extraordinario de este mes", "se solicita aclaración sobre un cargo comunitario"),
    ("obras", "medium", "Han aparecido grietas nuevas junto al acceso al cuarto de bicicletas.", "Grietas nuevas junto al cuarto de bicicletas", "han aparecido grietas nuevas en una zona común"),
    ("otros", "low", "Se ha encontrado una llave sin identificar en la entrada del portal.", "Llave sin identificar encontrada en el portal", "se ha encontrado un objeto sin identificar en el portal"),
]


def load_communities() -> list[str]:
    data = json.loads((PROJECT_ROOT / "data" / "communities.json").read_text(encoding="utf-8"))
    return [item["name"] for item in data]


def synthetic_phone(rng: random.Random) -> str:
    prefix = rng.choice([6, 7])
    return f"{prefix}{rng.randint(0, 99_999_999):08d}"


def property_reference(rng: random.Random) -> str:
    portal = rng.randint(1, 4)
    floor = rng.randint(1, 8)
    letter = rng.choice(LETTERS)
    return f"Portal {portal} · {floor}º {letter}"


def classification_for(case: tuple[str, str, str, str, str]) -> TriageClassification:
    category, priority, _description, summary, observation = case
    from app.core.enums import Category

    category_enum = Category(category)
    return TriageClassification(
        category=category_enum,
        priority=Priority(priority),
        summary=summary,
        department=CATEGORY_AREA_MAP[category_enum],
        reasoning=(
            f"Observación: {observation}. "
            "Acción: gestionar la incidencia según su riesgo y alcance. "
            f"Resultado: categoría {category} y prioridad {priority}."
        ),
    )


def corrected_classification(base: TriageClassification) -> TriageClassification:
    adjusted = {
        Priority.CRITICAL: Priority.HIGH,
        Priority.HIGH: Priority.MEDIUM,
        Priority.MEDIUM: Priority.HIGH,
        Priority.LOW: Priority.MEDIUM,
    }[base.priority]
    return base.model_copy(
        update={
            "priority": adjusted,
            "reasoning": (
                "Observación: revisión humana de la información disponible. "
                "Acción: ajustar el nivel de atención. "
                f"Resultado: prioridad corregida a {adjusted.value}."
            ),
        }
    )


def build_actions(
    received_at: datetime,
    status: IncidentOperationalStatus,
    rng: random.Random,
) -> list[IncidentAction]:
    actions = [
        IncidentAction(
            action_type=IncidentActionType.REGISTRATION,
            description="Incidencia registrada en ComunIA.",
            actor="Sistema",
            created_at=received_at,
        )
    ]

    if status == IncidentOperationalStatus.OPEN:
        return actions

    contact_time = received_at + timedelta(hours=rng.randint(1, 6))
    actions.append(
        IncidentAction(
            action_type=IncidentActionType.PROVIDER_CONTACT,
            description="Se contacta con el proveedor responsable y se traslada la incidencia.",
            actor="Administración",
            created_at=contact_time,
        )
    )

    if status == IncidentOperationalStatus.IN_PROGRESS:
        return actions

    if status == IncidentOperationalStatus.SCHEDULED:
        actions.append(
            IncidentAction(
                action_type=IncidentActionType.APPOINTMENT,
                description="Proveedor avisado. Visita técnica concertada.",
                actor="Administración",
                created_at=contact_time + timedelta(hours=2),
                scheduled_for=contact_time + timedelta(days=rng.randint(1, 4)),
            )
        )
        return actions

    visit_time = contact_time + timedelta(days=rng.randint(1, 3))
    actions.append(
        IncidentAction(
            action_type=IncidentActionType.PROVIDER_VISIT,
            description="El proveedor realiza una primera revisión de la incidencia.",
            actor="Administración",
            created_at=visit_time,
        )
    )

    if status == IncidentOperationalStatus.WAITING_PROVIDER:
        actions.append(
            IncidentAction(
                action_type=IncidentActionType.WAITING_MATERIAL,
                description="La intervención queda pendiente de pieza, material o nueva cita del proveedor.",
                actor="Administración",
                created_at=visit_time + timedelta(hours=1),
            )
        )
        return actions

    resolution_time = visit_time + timedelta(days=rng.randint(1, 4))
    actions.append(
        IncidentAction(
            action_type=IncidentActionType.RESOLUTION,
            description="Trabajo finalizado y funcionamiento comprobado por la administración.",
            actor="Administración",
            created_at=resolution_time,
        )
    )
    return actions


def demo_statuses(rng: random.Random) -> list[IncidentOperationalStatus]:
    """Ciclo de estados visibles en el panel operativo de la demo."""

    # `RESOLVED` se conserva en el enum solo por compatibilidad con datos
    # históricos, pero el producto utiliza `CLOSED` como estado final único.
    statuses = [
        IncidentOperationalStatus.OPEN,
        IncidentOperationalStatus.IN_PROGRESS,
        IncidentOperationalStatus.SCHEDULED,
        IncidentOperationalStatus.WAITING_PROVIDER,
        IncidentOperationalStatus.CLOSED,
    ]
    rng.shuffle(statuses)
    return statuses


def age_for_status(status: IncidentOperationalStatus, rng: random.Random) -> int:
    ranges = {
        IncidentOperationalStatus.OPEN: (0, 2),
        IncidentOperationalStatus.IN_PROGRESS: (1, 7),
        IncidentOperationalStatus.SCHEDULED: (2, 10),
        IncidentOperationalStatus.WAITING_PROVIDER: (5, 20),
        IncidentOperationalStatus.RESOLVED: (20, 55),
        IncidentOperationalStatus.CLOSED: (30, 60),
    }
    start, end = ranges[status]
    return rng.randint(start, end)


def generate_incidents(count: int, seed: int) -> list[TriageResponse]:
    rng = random.Random(seed)
    communities = load_communities()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    records: list[TriageResponse] = []
    case_pool = list(CASES)
    rng.shuffle(case_pool)
    status_pool = demo_statuses(rng)

    for index in range(1, count + 1):
        if (index - 1) % len(case_pool) == 0 and index > 1:
            rng.shuffle(case_pool)
        case = case_pool[(index - 1) % len(case_pool)]
        category, _priority, description, _summary, _observation = case
        classification = classification_for(case)
        status = status_pool[(index - 1) % len(status_pool)]
        if (index - 1) % len(status_pool) == 0 and index > 1:
            rng.shuffle(status_pool)
            status = status_pool[(index - 1) % len(status_pool)]
        age_days = age_for_status(status, rng)
        received_at = now - timedelta(
            days=age_days,
            hours=rng.randint(0, 20),
            minutes=rng.randint(0, 59),
        )
        provider = rng.choice([LLMProvider.OLLAMA, LLMProvider.GROQ])
        input_tokens = rng.randint(720, 1180)
        output_tokens = rng.randint(48, 95)
        if provider == LLMProvider.OLLAMA:
            latency_ms = round(rng.uniform(8_500, 38_000), 2)
            estimated_cost = 0.0
            model = "gemma3:4b"
        else:
            latency_ms = round(rng.uniform(280, 1_250), 2)
            estimated_cost = round(
                (input_tokens / 1_000_000 * 0.80)
                + (output_tokens / 1_000_000 * 4.00),
                7,
            )
            model = "qwen/qwen3.8-27b"

        review_choice = rng.choices(
            [HumanReviewStatus.PENDING, HumanReviewStatus.APPROVED, HumanReviewStatus.CORRECTED],
            weights=[25, 65, 10],
            k=1,
        )[0]
        human_classification = (
            corrected_classification(classification)
            if review_choice == HumanReviewStatus.CORRECTED
            else None
        )

        incident = IncidentRequest(
            text=description,
            channel=rng.choice(list(Channel)),
            community_reference=rng.choice(communities),
            property_reference=property_reference(rng),
            contact_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            contact_phone=synthetic_phone(rng),
            received_at=received_at,
        )

        deterministic_id = uuid5(
            NAMESPACE_URL,
            f"comunia-demo-{seed}-{index}",
        )

        records.append(
            TriageResponse(
                incident_id=deterministic_id,
                incident=incident,
                classification=classification,
                metrics=ProviderMetrics(
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    estimated_cost=estimated_cost,
                ),
                human_status=review_choice,
                human_classification=human_classification,
                operational_status=status,
                actions=build_actions(received_at, status, rng),
            )
        )

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Añade incidencias sintéticas para la demo de ComunIA.")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument(
        "--path",
        type=Path,
        default=PROJECT_ROOT / "data" / "incidents.json",
        help="Ruta del JSON de incidencias.",
    )
    parser.add_argument(
        "--remove-demo",
        action="store_true",
        help="Elimina los registros generados con esta semilla y count.",
    )
    args = parser.parse_args()

    args.path.parent.mkdir(parents=True, exist_ok=True)
    if args.path.exists():
        current = json.loads(args.path.read_text(encoding="utf-8"))
    else:
        current = []
    if not isinstance(current, list):
        raise SystemExit("El archivo de incidencias debe contener una lista JSON.")

    demo_records = generate_incidents(args.count, args.seed)
    demo_ids = {str(item.incident_id) for item in demo_records}

    if args.remove_demo:
        cleaned = [item for item in current if item.get("incident_id") not in demo_ids]
        args.path.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Eliminadas {len(current) - len(cleaned)} incidencias demo. Total actual: {len(cleaned)}")
        return

    existing_ids = {item.get("incident_id") for item in current}
    additions = [
        item.model_dump(mode="json")
        for item in demo_records
        if str(item.incident_id) not in existing_ids
    ]
    updated = [*current, *additions]
    temp_path = args.path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(args.path)

    print(f"Añadidas {len(additions)} incidencias demo sintéticas. Total actual: {len(updated)}")
    if len(additions) < args.count:
        print("Algunas ya existían con la misma semilla y no se duplicaron.")


if __name__ == "__main__":
    main()
