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


PROVIDER_LABELS = {
    "ollama": "Ollama · Local",
    "groq": "Groq · Externo",
}

PROVIDER_ICONS = {
    "ollama": "🖥️",
    "groq": "☁️",
}

PREFERENCE_LABELS = {
    "tie": "Ambos por igual",
    "ollama": "Ollama ofrece el mejor resultado",
    "groq": "Groq ofrece el mejor resultado",
    "neither": "Ninguno de los dos es satisfactorio",
}


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

            if isinstance(detail, list):
                messages = []
                field_names = {
                    "text": "Descripción de la incidencia",
                    "channel": "Canal",
                    "community_reference": "Comunidad",
                    "property_reference": "Vivienda / local / referencia",
                    "contact_name": "Persona de contacto",
                    "contact_phone": "Teléfono",
                    "reference_category": "Categoría de referencia",
                    "reference_priority": "Prioridad de referencia",
                    "preferred_result": "Preferencia humana",
                }

                for error in detail:
                    location = error.get("loc", [])
                    field = location[-1] if location else "campo"
                    field_name = field_names.get(field, field)
                    error_type = error.get("type", "")

                    if error_type == "string_too_short":
                        message = (
                            f"{field_name}: el campo es obligatorio "
                            "o demasiado corto."
                        )
                    elif error_type == "missing":
                        message = f"{field_name}: este campo es obligatorio."
                    else:
                        message = (
                            f"{field_name}: "
                            f"{error.get('msg', 'valor no válido')}"
                        )

                    messages.append(message)

                detail = "\n".join(messages)

        except ValueError:
            detail = response.text

        raise RuntimeError(str(detail))

    return response.json()


def format_latency(milliseconds: float) -> str:
    """Muestra milisegundos o segundos según el tamaño del valor."""

    if milliseconds >= 1000:
        return f"{milliseconds / 1000:.2f} s"
    return f"{milliseconds:.0f} ms"


def format_percentage(value: float | None) -> str:
    if value is None:
        return "Sin datos"
    return f"{value:.1f}%"


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
    col2.metric("Latencia", format_latency(metrics["latency_ms"]))
    col3.metric(
        "Tokens",
        metrics["input_tokens"] + metrics["output_tokens"],
    )
    col4.metric(
        "Coste estimado",
        f'${metrics["estimated_cost"]:.6f}',
    )
    st.caption(f'Modelo: {metrics["model"]}')
    if metrics["provider"] == "groq":
        st.caption(
            "El coste mostrado usa la tarifa pública de referencia; "
            "en Groq Free tier el coste facturado puede ser 0."
        )


def render_provider_comparison_card(provider_result: dict) -> None:
    """Tarjeta compacta para evitar métricas cortadas en columnas estrechas."""

    metrics = provider_result["metrics"]
    classification = provider_result["classification"]
    provider = metrics["provider"]

    with st.container(border=True):
        st.markdown(
            f"### {PROVIDER_ICONS.get(provider, '🤖')} "
            f"{PROVIDER_LABELS.get(provider, provider.upper())}"
        )
        st.caption(f'Modelo: {metrics["model"]}')

        class_col, priority_col = st.columns(2)
        class_col.metric("Categoría", classification["category"])
        priority_col.metric("Prioridad", classification["priority"].upper())

        st.markdown(f'**Área responsable:** `{classification["department"]}`')
        st.markdown(f'**Resumen:** {classification["summary"]}')

        with st.expander("Ver justificación del modelo"):
            st.write(classification["reasoning"])

        st.markdown("**Rendimiento**")
        metric_left, metric_right = st.columns(2)
        metric_left.metric(
            "Latencia",
            format_latency(metrics["latency_ms"]),
        )
        metric_right.metric(
            "Tokens totales",
            metrics["input_tokens"] + metrics["output_tokens"],
        )

        cost_left, cost_right = st.columns(2)
        cost_left.metric(
            "Entrada / salida",
            f'{metrics["input_tokens"]} / {metrics["output_tokens"]}',
        )
        cost_right.metric(
            "Coste ref.",
            f'${metrics["estimated_cost"]:.6f}',
        )

        if provider == "groq":
            st.caption(
                "Coste de referencia por tokens; en Free tier el coste "
                "facturado puede ser 0."
            )


def render_comparison_review(comparison: dict) -> None:
    """Permite crear o actualizar la referencia humana de calidad."""

    human_review = comparison.get("human_review")
    left, right = comparison["results"]

    default_category = (
        human_review["reference_category"]
        if human_review
        else left["classification"]["category"]
    )
    default_priority = (
        human_review["reference_priority"]
        if human_review
        else left["classification"]["priority"]
    )
    default_preference = (
        human_review["preferred_result"] if human_review else "tie"
    )
    default_notes = human_review.get("notes") or "" if human_review else ""

    st.subheader("👤 Evaluación humana de calidad")
    st.caption(
        "La persona supervisora fija la categoría y prioridad correctas. "
        "ComunIA calcula después el acierto de Ollama y Groq contra esa "
        "referencia, sin declarar un ganador automáticamente."
    )

    if human_review:
        st.success("Esta comparación ya tiene una validación humana guardada.")

        ref1, ref2, ref3 = st.columns(3)
        ref1.metric(
            "Categoría de referencia",
            human_review["reference_category"],
        )
        ref2.metric(
            "Prioridad de referencia",
            human_review["reference_priority"].upper(),
        )
        ref3.metric(
            "Preferencia humana",
            PREFERENCE_LABELS.get(
                human_review["preferred_result"],
                human_review["preferred_result"],
            ),
        )

        assessment_columns = st.columns(2)
        for column, assessment in zip(
            assessment_columns,
            human_review["assessments"],
            strict=True,
        ):
            with column:
                provider = assessment["provider"]
                with st.container(border=True):
                    st.markdown(
                        f"**{PROVIDER_ICONS.get(provider, '🤖')} "
                        f"{PROVIDER_LABELS.get(provider, provider)}**"
                    )
                    st.write(
                        "Categoría: "
                        + ("✅ correcta" if assessment["category_correct"] else "❌ distinta")
                    )
                    st.write(
                        "Prioridad: "
                        + ("✅ correcta" if assessment["priority_correct"] else "❌ distinta")
                    )
                    if assessment["exact_match"]:
                        st.success("Coincidencia exacta con la referencia humana")
                    else:
                        st.info(
                            f'Coincidencias: {assessment["quality_points"]}/2'
                        )

    category_values = [item.value for item in Category]
    priority_values = [item.value for item in Priority]
    preference_values = list(PREFERENCE_LABELS.keys())

    with st.expander(
        "Actualizar validación" if human_review else "Validar comparación",
        expanded=human_review is None,
    ):
        with st.form(f'comparison_review_{comparison["incident_id"]}'):
            form_left, form_right = st.columns(2)

            with form_left:
                reference_category = st.selectbox(
                    "Categoría correcta según supervisión humana",
                    category_values,
                    index=category_values.index(default_category),
                )
                reference_priority = st.selectbox(
                    "Prioridad correcta según supervisión humana",
                    priority_values,
                    index=priority_values.index(default_priority),
                )

            with form_right:
                preferred_result = st.selectbox(
                    "Valoración cualitativa global",
                    preference_values,
                    index=preference_values.index(default_preference),
                    format_func=lambda value: PREFERENCE_LABELS[value],
                )
                notes = st.text_area(
                    "Observaciones de la persona supervisora",
                    value=default_notes,
                    placeholder=(
                        "Opcional: comenta diferencias en resumen, razonamiento "
                        "o utilidad práctica."
                    ),
                )

            save_review = st.form_submit_button(
                "Guardar validación humana",
                use_container_width=True,
            )

        if save_review:
            try:
                updated = api_request(
                    "PATCH",
                    f'/comparisons/{comparison["incident_id"]}/review',
                    {
                        "reference_category": reference_category,
                        "reference_priority": reference_priority,
                        "preferred_result": preferred_result,
                        "notes": notes or None,
                    },
                )
                st.session_state["last_compare"] = updated
                st.success("Validación humana guardada.")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))


def render_quality_summary(summary: dict) -> None:
    """Muestra calidad acumulada contra la referencia humana."""

    st.subheader("📊 Calidad comparativa acumulada")

    total_col, reviewed_col = st.columns(2)
    total_col.metric("Comparaciones realizadas", summary["total_comparisons"])
    reviewed_col.metric(
        "Comparaciones validadas",
        summary["reviewed_comparisons"],
    )

    if summary["reviewed_comparisons"] == 0:
        st.info(
            "Aún no hay comparaciones validadas. Las tasas de calidad se "
            "calcularán cuando una persona defina la referencia correcta."
        )
        return

    columns = st.columns(2)
    for column, provider in zip(columns, summary["providers"], strict=True):
        with column:
            provider_name = provider["provider"]
            with st.container(border=True):
                st.markdown(
                    f"### {PROVIDER_ICONS.get(provider_name, '🤖')} "
                    f"{PROVIDER_LABELS.get(provider_name, provider_name)}"
                )

                accuracy_left, accuracy_right = st.columns(2)
                accuracy_left.metric(
                    "Acierto categoría",
                    format_percentage(provider["category_accuracy_pct"]),
                )
                accuracy_right.metric(
                    "Acierto prioridad",
                    format_percentage(provider["priority_accuracy_pct"]),
                )

                exact_left, preferred_right = st.columns(2)
                exact_left.metric(
                    "Coincidencia exacta",
                    format_percentage(provider["exact_match_rate_pct"]),
                )
                preferred_right.metric(
                    "Preferido por supervisor",
                    provider["preferred_count"],
                )

                st.caption(
                    f'Revisadas: {provider["reviewed"]} · '
                    f'Latencia media: '
                    f'{format_latency(provider["average_latency_ms"] or 0)} · '
                    f'Coste ref. acumulado: '
                    f'${provider["total_estimated_cost"]:.6f}'
                )

    st.caption(
        "La calidad se calcula únicamente sobre comparaciones revisadas por "
        "una persona: acierto de categoría, acierto de prioridad y coincidencia "
        "exacta de ambos campos. La preferencia humana es una señal cualitativa "
        "separada y no sustituye esas métricas."
    )


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
            ["ollama", "groq"],
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
        "Comparar Ollama vs Groq",
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
                {"incident": incident_payload},
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

    st.caption(f'Estado de revisión: {result["human_status"]}')


if "last_compare" in st.session_state:
    comparison = st.session_state["last_compare"]

    st.divider()
    st.subheader("🔎 Comparación Ollama vs Groq")
    st.caption(
        "Misma incidencia, misma entrada y mismo contrato Pydantic. "
        "Las diferencias visibles proceden del modelo y del proveedor."
    )
    st.caption(
        f'Comunidad identificada: '
        f'{comparison["incident"]["community_reference"]}'
    )

    columns = st.columns(2, gap="large")
    for column, provider_result in zip(
        columns,
        comparison["results"],
        strict=True,
    ):
        with column:
            render_provider_comparison_card(provider_result)

    left, right = comparison["results"]
    same_category = (
        left["classification"]["category"]
        == right["classification"]["category"]
    )
    same_priority = (
        left["classification"]["priority"]
        == right["classification"]["priority"]
    )

    if same_category and same_priority:
        st.success(
            "Los modelos coinciden en categoría y prioridad. "
            "La coincidencia no demuestra por sí sola que la clasificación "
            "sea correcta: debe validarla una persona."
        )
    else:
        st.warning(
            "Los modelos discrepan en al menos un campo de clasificación. "
            "La referencia humana determinará cuál se aproxima mejor."
        )

    comparison_rows = []
    for provider_result in comparison["results"]:
        metrics = provider_result["metrics"]
        classification = provider_result["classification"]
        comparison_rows.append(
            {
                "proveedor": metrics["provider"],
                "modelo": metrics["model"],
                "categoría": classification["category"],
                "prioridad": classification["priority"],
                "latencia": format_latency(metrics["latency_ms"]),
                "tokens": metrics["input_tokens"] + metrics["output_tokens"],
                "coste_ref": round(metrics["estimated_cost"], 8),
            }
        )

    st.markdown("**Resumen comparativo**")
    st.dataframe(
        comparison_rows,
        use_container_width=True,
        hide_index=True,
    )

    render_comparison_review(comparison)

    try:
        quality_summary = api_request("GET", "/comparisons/quality")
        render_quality_summary(quality_summary)
    except RuntimeError as exc:
        st.warning(f"No se pudo cargar la calidad acumulada: {exc}")


st.divider()
with st.expander("Histórico de incidencias"):
    if st.button("Actualizar histórico de incidencias"):
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
                st.dataframe(rows, use_container_width=True, hide_index=True)
        except RuntimeError as exc:
            st.error(str(exc))


with st.expander("Histórico de comparaciones y calidad"):
    if st.button("Actualizar histórico de comparaciones"):
        try:
            comparisons = api_request("GET", "/comparisons")
            if not comparisons:
                st.info("Todavía no hay comparaciones guardadas.")
            else:
                rows = []
                for item in comparisons:
                    review = item.get("human_review")
                    by_provider = {
                        result["metrics"]["provider"]: result
                        for result in item["results"]
                    }
                    rows.append(
                        {
                            "id": item["incident_id"],
                            "fecha": item["incident"]["received_at"],
                            "comunidad": item["incident"][
                                "community_reference"
                            ],
                            "ollama_categoria": by_provider["ollama"][
                                "classification"
                            ]["category"],
                            "groq_categoria": by_provider["groq"][
                                "classification"
                            ]["category"],
                            "ollama_prioridad": by_provider["ollama"][
                                "classification"
                            ]["priority"],
                            "groq_prioridad": by_provider["groq"][
                                "classification"
                            ]["priority"],
                            "validada": "sí" if review else "no",
                            "referencia_categoria": (
                                review["reference_category"] if review else "—"
                            ),
                            "referencia_prioridad": (
                                review["reference_priority"] if review else "—"
                            ),
                            "preferencia_humana": (
                                review["preferred_result"] if review else "—"
                            ),
                        }
                    )

                st.dataframe(rows, use_container_width=True, hide_index=True)

                quality_summary = api_request("GET", "/comparisons/quality")
                render_quality_summary(quality_summary)
        except RuntimeError as exc:
            st.error(str(exc))
