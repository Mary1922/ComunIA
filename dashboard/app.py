"""Dashboard Streamlit de ComunIA."""

from pathlib import Path
import os
import sys

import httpx
from dotenv import load_dotenv
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.enums import Category, Priority, ResponsibleArea  # noqa: E402


load_dotenv(PROJECT_ROOT / ".env")

API_BASE_URL = os.getenv(
    "COMUNIA_API_URL",
    "http://localhost:8000/api/v1",
).rstrip("/")


st.set_page_config(
    page_title="ComunIA",
    page_icon="🏢",
    layout="wide",
)

st.title("🏢 ComunIA")
st.caption(
    "Triaje asistido por IA para comunicaciones de comunidades de propietarios"
)


def api_request(
    method: str,
    endpoint: str,
    payload: dict | None = None,
) -> dict | list:
    """Llamada centralizada a FastAPI con mensajes de error legibles."""

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.request(
                method,
                f"{API_BASE_URL}{endpoint}",
                json=payload,
            )
    except httpx.RequestError as exc:
        raise RuntimeError(
            "No se puede conectar con la API. "
            "Comprueba que Uvicorn está ejecutándose."
        ) from exc

    if response.is_error:
        try:
            error_data = response.json()
            detail = error_data.get("detail", response.text)

            # Errores de validación de FastAPI / Pydantic
            if isinstance(detail, list):
                messages = []

                field_names = {
                    "text": "Descripción de la incidencia",
                    "channel": "Canal",
                    "community_reference": "Comunidad",
                    "property_reference": "Vivienda / local / referencia",
                    "contact_name": "Persona de contacto",
                    "contact_phone": "Teléfono",
                }

                for error in detail:
                    location = error.get("loc", [])
                    field = location[-1] if location else "campo"
                    field_name = field_names.get(field, field)

                    error_type = error.get("type", "")

                    if error_type == "string_too_short":
                        message = f"{field_name}: el campo es obligatorio o demasiado corto."

                    elif error_type == "missing":
                        message = f"{field_name}: este campo es obligatorio."

                    else:
                        message = f"{field_name}: {error.get('msg', 'valor no válido')}"

                    messages.append(message)

                detail = "\n".join(messages)

        except ValueError:
            detail = response.text

        raise RuntimeError(str(detail))

    return response.json()


def render_classification(classification: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Prioridad", classification["priority"].upper())
    col2.metric("Categoría", classification["category"])
    col3.metric("Área", classification["department"])

    st.markdown("**Resumen**")
    st.write(classification["summary"])

    st.markdown("**Justificación auditable**")
    st.write(classification["reasoning"])


def render_metrics(metrics: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Proveedor", metrics["provider"])
    col2.metric("Latencia", f'{metrics["latency_ms"]:.0f} ms')
    col3.metric(
        "Tokens",
        metrics["input_tokens"] + metrics["output_tokens"],
    )
    col4.metric(
        "Coste estimado",
        f'${metrics["estimated_cost"]:.6f}',
    )
    st.caption(f'Modelo: {metrics["model"]}')


with st.sidebar:
    st.header("Estado")
    try:
        health = api_request("GET", "/health")
        st.success(f'API conectada · {health["status"]}')
    except RuntimeError as exc:
        st.error(str(exc))


st.subheader("Nueva incidencia")

with st.form("incident_form"):
    col_left, col_right = st.columns(2)

    with col_left:
        channel = st.selectbox(
            "Canal *",
            ["email", "whatsapp", "phone"],
        )
        community_reference = st.text_input(
            "Comunidad *",
            placeholder="Ej.: Av. Democracia 110",
        )
        property_reference = st.text_input(
            "Vivienda / local / referencia *",
            placeholder="Ej.: Portal 2 - 3º B",
        )

    with col_right:
        contact_name = st.text_input("Persona de contacto *")
        contact_phone = st.text_input(
            "Teléfono *",
            placeholder="Ej.: 600123456",
        )
        provider = st.selectbox(
            "Proveedor para triaje",
            ["ollama", "openai"],
        )

    text = st.text_area(
        "Descripción de la incidencia *",
        height=150,
        placeholder=(
            "Describe qué ocurre, desde cuándo y si existe riesgo "
            "para personas o bienes."
        ),
    )

    col_a, col_b = st.columns(2)
    analyse = col_a.form_submit_button(
        "Analizar incidencia",
        use_container_width=True,
    )
    compare = col_b.form_submit_button(
        "Comparar Ollama vs OpenAI",
        use_container_width=True,
    )


incident_payload = {
    "text": text,
    "channel": channel,
    "community_reference": community_reference,
    "property_reference": property_reference,
    "contact_name": contact_name,
    "contact_phone": contact_phone,
}

# Comprobación previa de campos obligatorios en el formulario
required_fields = {
    "Comunidad": community_reference,
    "Vivienda / local / referencia": property_reference,
    "Persona de contacto": contact_name,
    "Teléfono": contact_phone,
    "Descripción de la incidencia": text,
}

missing_fields = [
    field_name
    for field_name, value in required_fields.items()
    if not value.strip()
]

if analyse:
    if missing_fields:
        st.error(
            "Debes completar los siguientes campos obligatorios: "
            + ", ".join(missing_fields)
        )
    else:
        try:
            result = api_request(
                "POST",
                "/triage",
                {
                    "incident": incident_payload,
                    "provider": provider,
                },
            )

            st.session_state["last_triage"] = result
            st.session_state.pop("last_compare", None)

        except RuntimeError as exc:
            st.error(str(exc))


if compare:
    if missing_fields:
        st.error(
            "Debes completar los siguientes campos obligatorios: "
            + ", ".join(missing_fields)
        )
    else:
        try:
            result = api_request(
                "POST",
                "/compare",
                {
                    "incident": incident_payload,
                },
            )

            st.session_state["last_compare"] = result
            st.session_state.pop("last_triage", None)

        except RuntimeError as exc:
            st.error(str(exc))

if "last_triage" in st.session_state:
    result = st.session_state["last_triage"]

    st.divider()
    st.subheader("Resultado del triaje")
    st.caption(
        f'Comunidad identificada: {result["incident"]["community_reference"]}'
    )

    render_classification(result["classification"])
    render_metrics(result["metrics"])

    st.subheader("Validación humana")

    if st.button("✓ Aprobar clasificación"):
        try:
            updated = api_request(
                "PATCH",
                f'/incidents/{result["incident_id"]}/review',
                {"status": "approved"},
            )
            st.session_state["last_triage"] = updated
            st.success("Clasificación aprobada.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

    with st.expander("Corregir clasificación"):
        current = result["classification"]

        with st.form("correction_form"):
            corrected_category = st.selectbox(
                "Categoría",
                [item.value for item in Category],
                index=[item.value for item in Category].index(
                    current["category"]
                ),
            )
            corrected_priority = st.selectbox(
                "Prioridad",
                [item.value for item in Priority],
                index=[item.value for item in Priority].index(
                    current["priority"]
                ),
            )

            maintenance_categories = {
                "ascensores",
                "fontaneria",
                "danos_agua",
                "electricidad",
                "antena_tv",
                "portero_automatico",
                "plagas",
                "jardin",
                "piscina",
                "limpieza",
                "garaje",
            }
            suggested_area = (
                ResponsibleArea.MANTENIMIENTO.value
                if corrected_category in maintenance_categories
                else ResponsibleArea.GESTION_COMUNIDAD.value
            )

            corrected_department = st.selectbox(
                "Área",
                [item.value for item in ResponsibleArea],
                index=[item.value for item in ResponsibleArea].index(
                    suggested_area
                ),
            )
            corrected_summary = st.text_input(
                "Resumen (máximo 10 palabras)",
                value=current["summary"],
            )
            corrected_reasoning = st.text_area(
                "Justificación",
                value=current["reasoning"],
            )

            submit_correction = st.form_submit_button(
                "Guardar corrección"
            )

        if submit_correction:
            payload = {
                "status": "corrected",
                "classification": {
                    "category": corrected_category,
                    "priority": corrected_priority,
                    "summary": corrected_summary,
                    "department": corrected_department,
                    "reasoning": corrected_reasoning,
                },
            }

            try:
                updated = api_request(
                    "PATCH",
                    f'/incidents/{result["incident_id"]}/review',
                    payload,
                )
                st.session_state["last_triage"] = updated
                st.success("Corrección humana guardada.")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    st.caption(
        f'Estado de revisión: {result["human_status"]}'
    )


if "last_compare" in st.session_state:
    comparison = st.session_state["last_compare"]

    st.divider()
    st.subheader("Comparación de proveedores")
    st.caption(
        "Misma incidencia, mismo contrato de salida y dos proveedores."
    )

    columns = st.columns(2)

    for column, provider_result in zip(
        columns,
        comparison["results"],
        strict=True,
    ):
        with column:
            provider_name = provider_result["metrics"]["provider"]
            st.markdown(f"### {provider_name.upper()}")
            render_classification(provider_result["classification"])
            render_metrics(provider_result["metrics"])

    left, right = comparison["results"]
    same_category = (
        left["classification"]["category"]
        == right["classification"]["category"]
    )
    same_priority = (
        left["classification"]["priority"]
        == right["classification"]["priority"]
    )

    st.info(
        "Coincidencia entre modelos · "
        f"categoría: {'sí' if same_category else 'no'} · "
        f"prioridad: {'sí' if same_priority else 'no'}. "
        "La calidad final debe ser validada por una persona."
    )


st.divider()
with st.expander("Histórico de incidencias"):
    if st.button("Actualizar histórico"):
        try:
            incidents = api_request("GET", "/incidents")
            if not incidents:
                st.info("Todavía no hay incidencias guardadas.")
            else:
                rows = []
                for item in incidents:
                    effective = (
                        item.get("human_classification")
                        or item["classification"]
                    )
                    rows.append(
                        {
                            "id": item["incident_id"],
                            "fecha": item["incident"]["received_at"],
                            "comunidad": item["incident"][
                                "community_reference"
                            ],
                            "categoría": effective["category"],
                            "prioridad": effective["priority"],
                            "estado": item["human_status"],
                            "proveedor": item["metrics"]["provider"],
                            "latencia_ms": item["metrics"]["latency_ms"],
                            "coste": item["metrics"]["estimated_cost"],
                        }
                    )
                st.dataframe(rows, use_container_width=True)

                st.markdown("**Calidad por proveedor (validación humana)**")
                provider_stats = {}
                for item in incidents:
                    provider_name = item["metrics"]["provider"]
                    stats = provider_stats.setdefault(
                        provider_name,
                        {
                            "procesadas": 0,
                            "revisadas": 0,
                            "aprobadas": 0,
                            "corregidas": 0,
                            "latencia_total": 0.0,
                            "coste_total": 0.0,
                        },
                    )
                    stats["procesadas"] += 1
                    stats["latencia_total"] += item["metrics"]["latency_ms"]
                    stats["coste_total"] += item["metrics"]["estimated_cost"]

                    if item["human_status"] in {"approved", "corrected"}:
                        stats["revisadas"] += 1
                    if item["human_status"] == "approved":
                        stats["aprobadas"] += 1
                    if item["human_status"] == "corrected":
                        stats["corregidas"] += 1

                quality_rows = []
                for provider_name, stats in provider_stats.items():
                    reviewed = stats["revisadas"]
                    approval_rate = (
                        stats["aprobadas"] / reviewed * 100
                        if reviewed
                        else None
                    )
                    quality_rows.append(
                        {
                            "proveedor": provider_name,
                            "procesadas": stats["procesadas"],
                            "revisadas": reviewed,
                            "tasa_aprobacion_%": (
                                round(approval_rate, 1)
                                if approval_rate is not None
                                else "sin datos"
                            ),
                            "correcciones": stats["corregidas"],
                            "latencia_media_ms": round(
                                stats["latencia_total"]
                                / stats["procesadas"],
                                1,
                            ),
                            "coste_total": round(
                                stats["coste_total"],
                                8,
                            ),
                        }
                    )

                st.dataframe(quality_rows, use_container_width=True)
                st.caption(
                    "La tasa de aprobación se usa como indicador práctico "
                    "de calidad: solo se calcula sobre incidencias revisadas "
                    "por una persona."
                )
        except RuntimeError as exc:
            st.error(str(exc))
