"""Dashboard Streamlit de ComunIA."""

from collections import defaultdict
from datetime import datetime
from html import escape
import json
from pathlib import Path
import os
import sys

import httpx
from dotenv import load_dotenv
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.enums import (  # noqa: E402
    Category,
    IncidentActionType,
    IncidentOperationalStatus,
    Priority,
    ResponsibleArea,
)
from app.core.validators import is_valid_spanish_phone  # noqa: E402
from app.services.notification_service import build_whatsapp_demo_message  # noqa: E402


load_dotenv(PROJECT_ROOT / ".env")

API_BASE_URL = os.getenv(
    "COMUNIA_API_URL",
    "http://localhost:8000/api/v1",
).rstrip("/")
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_TRIAGE_PROVIDER = os.getenv("DEFAULT_TRIAGE_PROVIDER", "ollama").lower()


st.set_page_config(
    page_title="ComunIA",
    page_icon="🏢",
    layout="wide",
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


PRIORITY_LABELS = {
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Media",
    "low": "Baja",
}

CATEGORY_LABELS = {
    "ascensores": "Ascensores",
    "fontaneria": "Fontanería",
    "danos_agua": "Daños de agua",
    "electricidad": "Electricidad",
    "antena_tv": "Antena de TV",
    "portero_automatico": "Portero automático",
    "plagas": "Plagas",
    "jardin": "Jardín",
    "piscina": "Piscina",
    "seguridad": "Seguridad",
    "limpieza": "Limpieza",
    "zonas_comunes": "Zonas comunes",
    "garaje": "Garaje",
    "convivencia": "Convivencia",
    "administracion": "Administración",
    "contabilidad": "Contabilidad",
    "obras": "Obras",
    "otros": "Otros",
}

AREA_LABELS = {
    "mantenimiento": "Mantenimiento",
    "gestion_comunidad": "Gestión de comunidad",
}

STATUS_LABELS = {
    "pending": "Pendiente de revisión",
    "approved": "Aprobada",
    "corrected": "Corregida",
}

OPERATIONAL_STATUS_LABELS = {
    "open": "Abierta",
    "in_progress": "En gestión",
    "scheduled": "Cita programada",
    "waiting_provider": "Pendiente de proveedor",
    "resolved": "Cerrada",  # compatibilidad con registros antiguos
    "closed": "Cerrada",
}

ACTION_TYPE_LABELS = {
    "registration": "Registro de incidencia",
    "provider_contact": "Aviso / contacto con proveedor",
    "appointment": "Cita concertada",
    "provider_visit": "Visita del proveedor",
    "waiting_material": "Pendiente de pieza o material",
    "internal_note": "Nota de seguimiento",
    "resolution": "Resolución",
}

CHANNEL_LABELS = {
    "email": "Correo electrónico",
    "whatsapp": "WhatsApp",
    "phone": "Teléfono",
}


def load_custom_css() -> None:
    """Carga el sistema visual del dashboard desde un CSS independiente."""

    css_path = ASSETS_DIR / "style.css"
    if not css_path.exists():
        return

    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


def load_registered_communities() -> list[str]:
    """Devuelve todas las comunidades maestras del proyecto."""

    path = PROJECT_ROOT / "data" / "communities.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return sorted(
        {item.get("name", "").strip() for item in raw if item.get("name")}
    )


def render_hero() -> None:
    """Cabecera de producto: identidad, propósito y pilares técnicos."""

    st.markdown(
        """
        <section class="comunia-hero">
            <div class="hero-kicker">🌿 IA aplicada a la gestión residencial</div>
            <h1 class="hero-title">Comun<span class="accent">IA</span></h1>
            <p class="hero-subtitle">
                Gestión inteligente de incidencias para comunidades de propietarios:
                registro, triaje, seguimiento y supervisión humana en un único panel.
            </p>
            <div class="hero-tags">
                <span class="hero-tag">📨 Registro centralizado</span>
                <span class="hero-tag">🧠 Triaje asistido</span>
                <span class="hero-tag">🗓️ Seguimiento cronológico</span>
                <span class="hero-tag">👤 Supervisión humana</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(icon: str, title: str, subtitle: str = "") -> None:
    """Cabecera consistente sin HTML fragmentado por Markdown."""

    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    html = (
        '<div class="section-heading">'
        f'<div class="section-icon">{icon}</div>'
        '<div class="section-copy">'
        f'<h2>{escape(title)}</h2>'
        f'{subtitle_html}'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


load_custom_css()
render_hero()


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


def priority_label(value: str) -> str:
    return PRIORITY_LABELS.get(value, value)


def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(value, value.replace("_", " ").title())


def area_label(value: str) -> str:
    return AREA_LABELS.get(value, value.replace("_", " ").title())


def status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def format_received_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y · %H:%M")
    except (TypeError, ValueError):
        return value


def incident_date_key(value: str) -> str:
    """Devuelve YYYY-MM-DD para filtros, o el valor original si no se puede parsear."""

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return value


def date_filter_label(value: str) -> str:
    if value == "Todas":
        return "Todas"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value


def phone_validation_message(value: str) -> str | None:
    """Mensaje de validación para teléfonos españoles de 9 cifras."""

    if is_valid_spanish_phone(value):
        return None
    return "El teléfono debe contener exactamente 9 cifras y solo números."


def build_public_incident_references(incidents: list[dict]) -> dict[str, str]:
    """Genera referencias legibles sin sustituir el UUID interno.

    La numeración es cronológica e independiente por año. Como ComunIA no
    elimina incidencias desde el dashboard, la referencia permanece estable
    durante el uso normal del prototipo.
    """

    counters: defaultdict[int, int] = defaultdict(int)
    references: dict[str, str] = {}

    ordered = sorted(
        incidents,
        key=lambda item: item.get("incident", {}).get("received_at", ""),
    )

    for item in ordered:
        received_at = item.get("incident", {}).get("received_at", "")
        try:
            year = datetime.fromisoformat(
                received_at.replace("Z", "+00:00")
            ).year
        except (TypeError, ValueError):
            year = datetime.now().year

        counters[year] += 1
        references[item["incident_id"]] = (
            f"Incidencia {counters[year]}-{year}"
        )

    return references


def build_public_comparison_references(
    comparisons: list[dict],
) -> dict[str, str]:
    """Genera referencias legibles para comparaciones sin exponer el UUID."""

    counters: defaultdict[int, int] = defaultdict(int)
    references: dict[str, str] = {}

    ordered = sorted(
        comparisons,
        key=lambda item: item.get("incident", {}).get("received_at", ""),
    )

    for item in ordered:
        received_at = item.get("incident", {}).get("received_at", "")
        try:
            year = datetime.fromisoformat(
                received_at.replace("Z", "+00:00")
            ).year
        except (TypeError, ValueError):
            year = datetime.now().year

        counters[year] += 1
        references[item["incident_id"]] = (
            f"Comparación {counters[year]}-{year}"
        )

    return references


def comparison_for_incident(
    comparisons: list[dict],
    incident_id: str,
) -> dict | None:
    """Devuelve la comparación vinculada a una incidencia del histórico."""

    return next(
        (
            comparison
            for comparison in comparisons
            if str(comparison.get("source_incident_id")) == str(incident_id)
        ),
        None,
    )


def render_summary_box(summary: str) -> None:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-icon">📝</div>
            <div>
                <div class="summary-label">Resumen ejecutivo</div>
                <div class="summary-text">{escape(summary)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_classification(classification: dict) -> None:
    priority = classification["priority"]
    visible_priority = priority_label(priority)
    visible_category = category_label(classification["category"])
    visible_area = area_label(classification["department"])

    st.markdown(
        f"""
        <div class="classification-strip">
            <span class="status-pill priority-{priority}">⚠️ {visible_priority}</span>
            <span class="classification-pill">🧩 {visible_category}</span>
            <span class="classification-pill">🛠️ {visible_area}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="classification-grid">
            <div class="classification-card">
                <div class="classification-card-label">Prioridad</div>
                <div class="classification-card-value">{escape(visible_priority)}</div>
            </div>
            <div class="classification-card">
                <div class="classification-card-label">Categoría</div>
                <div class="classification-card-value">{escape(visible_category)}</div>
            </div>
            <div class="classification-card">
                <div class="classification-card-label">Área</div>
                <div class="classification-card-value">{escape(visible_area)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_summary_box(classification["summary"])

    with st.expander("🧠 Ver trazabilidad ReAct auditable", expanded=True):
        st.write(classification["reasoning"])




def _cache_updated_incident(updated: dict) -> None:
    """Sincroniza una revisión humana en las cachés de Streamlit."""

    incident_id = updated["incident_id"]

    if (
        "last_triage" in st.session_state
        and st.session_state["last_triage"].get("incident_id") == incident_id
    ):
        st.session_state["last_triage"] = updated

    if "incident_history" in st.session_state:
        st.session_state["incident_history"] = [
            updated if item.get("incident_id") == incident_id else item
            for item in st.session_state["incident_history"]
        ]


def _set_incident_review_feedback(incident_id: str, message: str) -> None:
    st.session_state["incident_review_feedback"] = {
        "incident_id": incident_id,
        "message": message,
    }


def render_incident_review_feedback(incident_id: str) -> None:
    """Muestra una confirmación después de aprobar o corregir una incidencia."""

    feedback = st.session_state.get("incident_review_feedback")
    if not feedback or feedback.get("incident_id") != incident_id:
        return

    st.success(feedback["message"])
    st.toast(feedback["message"], icon="✅")
    st.session_state.pop("incident_review_feedback", None)


def render_incident_review_controls(
    incident: dict,
    key_prefix: str,
    *,
    show_heading: bool = True,
) -> None:
    """Permite aprobar o corregir una incidencia pendiente de revisión."""

    if incident.get("human_status") != "pending":
        st.caption(
            f'Estado de revisión: {status_label(incident.get("human_status", "pending"))}'
        )
        return

    if show_heading:
        render_section_header(
            "✅",
            "Validación humana",
            "Aprueba la propuesta del modelo o corrige la clasificación antes del registro final.",
        )

    if st.button(
        "✓ Aprobar clasificación",
        key=f"{key_prefix}_approve",
        type="primary",
    ):
        try:
            updated = api_request(
                "PATCH",
                f'/incidents/{incident["incident_id"]}/review',
                {"status": "approved"},
            )
            _cache_updated_incident(updated)
            _set_incident_review_feedback(
                incident["incident_id"],
                "Clasificación aprobada correctamente.",
            )
            st.session_state.pop("history_review_open_for", None)
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

    with st.expander(
        "Corregir clasificación",
        expanded=st.session_state.get("history_review_open_for")
        == incident["incident_id"],
    ):
        current = incident["classification"]

        with st.form(f"{key_prefix}_correction_form"):
            category_values = [item.value for item in Category]
            priority_values = [item.value for item in Priority]
            area_values = [item.value for item in ResponsibleArea]

            corrected_category = st.selectbox(
                "Categoría",
                category_values,
                index=category_values.index(current["category"]),
                format_func=category_label,
                key=f"{key_prefix}_category",
            )
            corrected_priority = st.selectbox(
                "Prioridad",
                priority_values,
                index=priority_values.index(current["priority"]),
                format_func=priority_label,
                key=f"{key_prefix}_priority",
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
                area_values,
                index=area_values.index(suggested_area),
                format_func=area_label,
                key=f"{key_prefix}_department",
            )
            corrected_summary = st.text_input(
                "Resumen (máximo 10 palabras)",
                value=current["summary"],
                key=f"{key_prefix}_summary",
            )
            corrected_reasoning = st.text_area(
                "Justificación",
                value=current["reasoning"],
                key=f"{key_prefix}_reasoning",
            )

            submit_correction = st.form_submit_button(
                "Guardar corrección",
                type="primary",
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
                    f'/incidents/{incident["incident_id"]}/review',
                    payload,
                )
                _cache_updated_incident(updated)
                _set_incident_review_feedback(
                    incident["incident_id"],
                    "Corrección humana guardada correctamente.",
                )
                st.session_state.pop("history_review_open_for", None)
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    st.caption("Estado de revisión: Pendiente de revisión")

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
    """Tarjeta visual de proveedor con clasificación y rendimiento."""

    metrics = provider_result["metrics"]
    classification = provider_result["classification"]
    provider = metrics["provider"]
    chip_class = "local" if provider == "ollama" else "external"
    priority = classification["priority"]

    with st.container(border=True):
        st.markdown('<span class="opaque-work-card-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <span class="provider-chip {chip_class}">
                {PROVIDER_ICONS.get(provider, '🤖')}
                {PROVIDER_LABELS.get(provider, provider.upper())}
            </span>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"### {metrics['model']}")
        st.markdown(
            '<div class="supporting-copy">Modelo utilizado en esta inferencia</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="classification-strip">
                <span class="status-pill priority-{priority}">⚠️ {priority_label(priority)}</span>
                <span class="classification-pill">🧩 {category_label(classification['category'])}</span>
                <span class="classification-pill">🛠️ {area_label(classification['department'])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_summary_box(classification["summary"])

        with st.expander("🧠 Trazabilidad ReAct auditable"):
            st.write(classification["reasoning"])

        st.markdown("**⚡ Rendimiento**")
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

    render_section_header(
        "👤",
        "Evaluación humana de calidad",
        "Define la referencia correcta y valida la calidad real de cada modelo.",
    )

    if human_review:
        st.success("Esta comparación ya tiene una validación humana guardada.")

        ref1, ref2, ref3 = st.columns(3)
        ref1.metric(
            "Categoría de referencia",
            category_label(human_review["reference_category"]),
        )
        ref2.metric(
            "Prioridad de referencia",
            priority_label(human_review["reference_priority"]),
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
                    st.markdown('<span class="opaque-work-card-marker"></span>', unsafe_allow_html=True)
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
                    format_func=category_label,
                )
                reference_priority = st.selectbox(
                    "Prioridad correcta según supervisión humana",
                    priority_values,
                    index=priority_values.index(default_priority),
                    format_func=priority_label,
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

    render_section_header(
        "📊",
        "Calidad comparativa acumulada",
        "Resultados acumulados de comparaciones ya validadas por una persona.",
    )

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
                st.markdown('<span class="opaque-work-card-marker"></span>', unsafe_allow_html=True)
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

                st.markdown(
                    '<div class="quality-footnote">'
                    f'Revisadas: {provider["reviewed"]} · '
                    f'Latencia media: {format_latency(provider["average_latency_ms"] or 0)} · '
                    f'Coste ref. acumulado: ${provider["total_estimated_cost"]:.6f}'
                    '</div>',
                    unsafe_allow_html=True,
                )

    with st.expander("ℹ️ Cómo se calcula la calidad", expanded=False):
        st.caption(
            "La calidad se calcula únicamente sobre comparaciones revisadas por "
            "una persona: acierto de categoría, acierto de prioridad y coincidencia "
            "exacta de ambos campos. La preferencia humana es una señal cualitativa "
            "separada y no sustituye esas métricas."
        )


def canonical_operational_status(value: str | None) -> str:
    """Unifica el estado histórico `resolved` con el estado visible `closed`."""

    if value == "resolved":
        return "closed"
    return value or "open"


def operational_status_label(value: str) -> str:
    canonical = canonical_operational_status(value)
    return OPERATIONAL_STATUS_LABELS.get(
        canonical, canonical.replace("_", " ").title()
    )


def action_type_label(value: str) -> str:
    return ACTION_TYPE_LABELS.get(value, value.replace("_", " ").title())


def get_effective_classification(incident: dict) -> dict:
    """Usa la corrección humana cuando exista; si no, la propuesta del LLM."""

    return incident.get("human_classification") or incident["classification"]


def render_operational_kpis(incidents: list[dict]) -> None:
    active_statuses = {"open", "in_progress", "scheduled", "waiting_provider"}
    open_count = sum(
        item.get("operational_status", "open") in active_statuses
        for item in incidents
    )
    pending_review = sum(item.get("human_status") == "pending" for item in incidents)
    urgent_count = sum(
        item.get("operational_status", "open") in active_statuses
        and get_effective_classification(item).get("priority") in {"critical", "high"}
        for item in incidents
    )
    closed_count = sum(
        canonical_operational_status(item.get("operational_status")) == "closed"
        for item in incidents
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Incidencias abiertas", open_count)
    col2.metric("Pendientes de validación", pending_review)
    col3.metric("Críticas / altas abiertas", urgent_count)
    col4.metric("Incidencias cerradas", closed_count)


def render_operational_timeline(incident: dict) -> None:
    """Renderiza el histórico en un único bloque HTML, sin Markdown intermedio."""

    actions = list(incident.get("actions") or [])
    has_registration = any(
        item.get("action_type") == "registration" for item in actions
    )
    if not has_registration:
        actions.append(
            {
                "action_type": "registration",
                "description": "Incidencia registrada en ComunIA.",
                "actor": "Sistema",
                "created_at": incident["incident"]["received_at"],
                "scheduled_for": None,
            }
        )

    actions.sort(key=lambda item: item.get("created_at", ""))

    if not actions:
        st.info("Todavía no hay actuaciones registradas.")
        return

    timeline_items: list[str] = []
    for index, action in enumerate(actions, start=1):
        scheduled = action.get("scheduled_for")
        scheduled_html = ""
        if scheduled:
            scheduled_html = (
                '<div class="timeline-scheduled">📅 Próxima fecha: '
                f'{escape(format_received_at(scheduled))}</div>'
            )

        # Sin saltos de línea ni sangrías: Markdown no puede interpretar partes
        # del HTML como bloques de código y mostrar etiquetas </div> en pantalla.
        timeline_items.append(
            '<div class="timeline-item">'
            f'<div class="timeline-index">{index}</div>'
            '<div class="timeline-content">'
            f'<div class="timeline-title">{escape(action_type_label(action["action_type"]))}</div>'
            f'<div class="timeline-date">{escape(format_received_at(action["created_at"]))} · '
            f'{escape(action.get("actor") or "Administración")}</div>'
            f'<div class="timeline-description">{escape(action["description"])}</div>'
            f'{scheduled_html}'
            '</div>'
            '</div>'
        )

    timeline_html = '<div class="timeline">' + ''.join(timeline_items) + '</div>'
    st.markdown(timeline_html, unsafe_allow_html=True)


def render_operational_incident_detail(incident: dict, public_reference: str) -> None:
    classification = get_effective_classification(incident)
    operational_status = canonical_operational_status(
        incident.get("operational_status", "open")
    )

    action_success_id = st.session_state.pop("operational_action_success_id", None)
    if action_success_id == incident["incident_id"]:
        st.success("✅ Actuación registrada correctamente en el seguimiento.")
        if hasattr(st, "toast"):
            st.toast("Actuación registrada correctamente", icon="✅")

    st.markdown(
        f"""
        <div class="operational-detail-header">
            <div>
                <div class="operational-reference">{escape(public_reference)}</div>
                <div class="operational-address">{escape(incident['incident']['community_reference'])} · {escape(incident['incident']['property_reference'])}</div>
            </div>
            <span class="operation-status operation-{escape(operational_status)}">{escape(operational_status_label(operational_status))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Prioridad", priority_label(classification["priority"]))
    c2.metric("Categoría", category_label(classification["category"]))
    c3.metric("Revisión IA", status_label(incident.get("human_status", "pending")))

    render_summary_box(classification["summary"])

    with st.expander("📄 Datos del aviso", expanded=False):
        st.write(f'**Descripción:** {incident["incident"]["text"]}')
        st.write(f'**Contacto:** {incident["incident"]["contact_name"]} · {incident["incident"]["contact_phone"]}')
        st.write(f'**Canal:** {CHANNEL_LABELS.get(incident["incident"]["channel"], incident["incident"]["channel"])}')
        st.write(f'**Recibida:** {format_received_at(incident["incident"]["received_at"])}')

    st.caption(
        "Histórico cronológico de llamadas, citas, visitas y actuaciones hasta su resolución."
    )
    render_operational_timeline(incident)

    with st.expander("➕ Registrar nueva actuación", expanded=False):
        action_values = [item.value for item in IncidentActionType]
        status_values = [
            "open",
            "in_progress",
            "scheduled",
            "waiting_provider",
            "closed",
        ]
        current_status = canonical_operational_status(
            incident.get("operational_status", "open")
        )
        version_key = f'action_form_version_{incident["incident_id"]}'
        form_version = st.session_state.get(version_key, 0)
        field_suffix = f'{incident["incident_id"]}_{form_version}'

        with st.form(f'operational_action_{field_suffix}'):
            left, right = st.columns(2)
            with left:
                action_type = st.selectbox(
                    "Tipo de actuación",
                    action_values,
                    format_func=action_type_label,
                    key=f'action_type_{field_suffix}',
                )
                actor = st.text_input(
                    "Registrado por",
                    value="Administración",
                    key=f'action_actor_{field_suffix}',
                )
            with right:
                new_status = st.selectbox(
                    "Estado después de esta actuación",
                    status_values,
                    index=status_values.index(current_status),
                    format_func=operational_status_label,
                    key=f'action_status_{field_suffix}',
                )
                has_schedule = st.checkbox(
                    "Añadir fecha o cita futura",
                    key=f'action_schedule_enabled_{field_suffix}',
                )

            description = st.text_area(
                "Detalle de la actuación",
                placeholder=(
                    "Ej.: Avisado mantenimiento de antenas. Cita concertada "
                    "para el martes a las 10:00."
                ),
                height=100,
                key=f'action_description_{field_suffix}',
            )

            scheduled_for = None
            if has_schedule:
                schedule_left, schedule_right = st.columns(2)
                scheduled_date = schedule_left.date_input(
                    "Fecha prevista",
                    key=f'action_date_{field_suffix}',
                )
                scheduled_time = schedule_right.time_input(
                    "Hora prevista",
                    key=f'action_time_{field_suffix}',
                )
                scheduled_for = datetime.combine(
                    scheduled_date,
                    scheduled_time,
                ).isoformat()

            save_action = st.form_submit_button(
                "Guardar actuación",
                use_container_width=True,
            )

        if save_action:
            if not description.strip():
                st.error("Describe brevemente la actuación realizada.")
            else:
                payload = {
                    "action_type": action_type,
                    "description": description,
                    "actor": actor or "Administración",
                    "new_status": new_status,
                    "scheduled_for": scheduled_for,
                }
                try:
                    updated = api_request(
                        "POST",
                        f'/incidents/{incident["incident_id"]}/actions',
                        payload,
                    )
                    st.session_state["operational_selected_incident"] = updated["incident_id"]
                    st.session_state["operational_action_success_id"] = updated["incident_id"]
                    # Cambiar la versión del formulario crea widgets nuevos y
                    # deja el detalle de la actuación en blanco tras guardar.
                    st.session_state[version_key] = form_version + 1
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))


def render_operational_registration() -> None:
    with st.expander("➕ Registrar nueva incidencia", expanded=False):
        with st.form("operational_incident_form"):
            col_left, col_right = st.columns(2)
            with col_left:
                channel = st.selectbox(
                    "Canal *",
                    ["email", "whatsapp", "phone"],
                    format_func=lambda value: CHANNEL_LABELS[value],
                    key="ops_channel",
                )
                community_reference = st.text_input(
                    "Comunidad *",
                    placeholder="Ej.: Av. Democracia 110",
                    key="ops_community",
                )
                property_reference = st.text_input(
                    "Vivienda / local / referencia *",
                    placeholder="Ej.: Portal 2 - 3º B",
                    key="ops_property",
                )
            with col_right:
                contact_name = st.text_input(
                    "Persona de contacto *",
                    key="ops_contact",
                )
                contact_phone = st.text_input(
                    "Teléfono *",
                    placeholder="Ej.: 600123456",
                    max_chars=9,
                    key="ops_phone",
                    help="Introduce exactamente 9 cifras, sin espacios ni prefijos.",
                )

            text = st.text_area(
                "Descripción de la incidencia *",
                height=130,
                placeholder="Describe qué ocurre y desde cuándo.",
                key="ops_text",
            )
            submit = st.form_submit_button(
                "Registrar y clasificar",
                use_container_width=True,
            )

        if submit:
            values = {
                "Comunidad": community_reference,
                "Vivienda / local / referencia": property_reference,
                "Persona de contacto": contact_name,
                "Teléfono": contact_phone,
                "Descripción": text,
            }
            missing = [name for name, value in values.items() if not value.strip()]
            phone_error = phone_validation_message(contact_phone)
            if missing:
                st.error("Debes completar: " + ", ".join(missing))
            elif phone_error:
                st.error(phone_error)
            else:
                try:
                    result = api_request(
                        "POST",
                        "/triage",
                        {
                            "incident": {
                                "text": text,
                                "channel": channel,
                                "community_reference": community_reference,
                                "property_reference": property_reference,
                                "contact_name": contact_name,
                                "contact_phone": contact_phone,
                            },
                            "provider": DEFAULT_TRIAGE_PROVIDER,
                        },
                    )
                    st.session_state["operational_selected_incident"] = result["incident_id"]
                    # Guardamos un mensaje flash antes del rerun. En la siguiente
                    # renderización podremos calcular y mostrar la referencia
                    # pública (p. ej. "Incidencia 7-2026") en lugar del UUID.
                    st.session_state["operational_registration_success_id"] = result["incident_id"]
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))


def render_whatsapp_demo_preview(incident: dict, public_reference: str) -> None:
    """Previsualiza un aviso de WhatsApp sin realizar ningún envío real."""

    incident_data = incident.get("incident", {})
    classification = get_effective_classification(incident)
    message = build_whatsapp_demo_message(
        contact_name=incident_data.get("contact_name", ""),
        public_reference=public_reference,
        summary=classification.get("summary", ""),
    )

    st.markdown(
        '<div class="whatsapp-demo-card">'
        '<div class="whatsapp-demo-heading">💬 Previsualización de WhatsApp</div>'
        '<div class="whatsapp-demo-meta">'
        f'Destinatario: {escape(incident_data.get("contact_phone", ""))}'
        '</div>'
        f'<div class="whatsapp-demo-message">{escape(message).replace(chr(10), "<br>")}</div>'
        '<div class="whatsapp-demo-badge">Modo demostración · Ningún mensaje ha sido enviado</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "Cerrar previsualización",
        key=f'close_whatsapp_preview_{incident["incident_id"]}',
    ):
        st.session_state.pop("whatsapp_preview_incident_id", None)
        st.rerun()


def render_operational_dashboard() -> None:
    render_section_header(
        "🗂️",
        "Panel operativo de incidencias",
    )

    try:
        incidents = api_request("GET", "/incidents")
    except RuntimeError as exc:
        st.error(str(exc))
        return

    public_refs = build_public_incident_references(incidents) if incidents else {}

    # Mensaje de confirmación posterior al registro. Se muestra una sola vez y
    # utiliza la referencia amigable que ve el personal administrativo.
    registered_incident_id = st.session_state.get(
        "operational_registration_success_id"
    )
    if registered_incident_id:
        public_reference = public_refs.get(registered_incident_id, "Incidencia")
        success_message = (
            f"✅ {public_reference} registrada correctamente. "
            "Ya está disponible en la bandeja de incidencias."
        )
        st.success(success_message)
        if hasattr(st, "toast"):
            st.toast(
                f"{public_reference} registrada correctamente",
                icon="✅",
            )

        registered_incident = next(
            (item for item in incidents if item["incident_id"] == registered_incident_id),
            None,
        )
        if registered_incident is not None:
            if st.button(
                "💬 Preparar WhatsApp al contacto",
                key=f"prepare_whatsapp_{registered_incident_id}",
                use_container_width=False,
            ):
                st.session_state["whatsapp_preview_incident_id"] = registered_incident_id
                st.session_state.pop("operational_registration_success_id", None)
                st.rerun()

    whatsapp_preview_id = st.session_state.get("whatsapp_preview_incident_id")
    if whatsapp_preview_id:
        preview_incident = next(
            (item for item in incidents if item["incident_id"] == whatsapp_preview_id),
            None,
        )
        if preview_incident is not None:
            render_whatsapp_demo_preview(
                preview_incident,
                public_refs.get(whatsapp_preview_id, "Incidencia"),
            )
        else:
            st.session_state.pop("whatsapp_preview_incident_id", None)

    render_operational_kpis(incidents)
    render_operational_registration()

    if not incidents:
        st.info("Todavía no hay incidencias registradas.")
        return

    with st.expander("🔎 Bandeja de incidencias", expanded=False):
        st.caption(
            "Filtra la cartera de trabajo y abre una incidencia para consultar o actualizar su seguimiento."
        )

        filter1, filter2, filter3 = st.columns(3)
        status_filter = filter1.selectbox(
            "Estado operativo",
            ["Todas", "open", "in_progress", "scheduled", "waiting_provider", "closed"],
            format_func=lambda value: "Todos" if value == "Todas" else operational_status_label(value),
            key="ops_status_filter",
        )
        priority_filter = filter2.selectbox(
            "Prioridad",
            ["Todas", *[item.value for item in Priority]],
            format_func=lambda value: "Todas" if value == "Todas" else priority_label(value),
            key="ops_priority_filter",
        )
        category_filter = filter3.selectbox(
            "Categoría",
            ["Todas", *[item.value for item in Category]],
            format_func=lambda value: "Todas" if value == "Todas" else category_label(value),
            key="ops_category_filter",
        )

        filter4, filter5, filter6 = st.columns(3)
        communities = sorted(
            set(load_registered_communities())
            | {item["incident"]["community_reference"] for item in incidents}
        )
        community_filter = filter4.selectbox(
            "Comunidad",
            ["Todas", *communities],
            key="ops_community_filter",
        )
        incident_dates = sorted(
            {incident_date_key(item["incident"]["received_at"]) for item in incidents},
            reverse=True,
        )
        date_filter = filter5.selectbox(
            "Fecha",
            ["Todas", *incident_dates],
            format_func=date_filter_label,
            key="ops_date_filter",
        )
        contacts = sorted({item["incident"]["contact_name"] for item in incidents})
        contact_filter = filter6.selectbox(
            "Persona de contacto",
            ["Todas", *contacts],
            key="ops_contact_filter",
        )


        filtered = []
        for item in incidents:
            classification = get_effective_classification(item)
            if (
                status_filter != "Todas"
                and canonical_operational_status(item.get("operational_status", "open"))
                != status_filter
            ):
                continue
            if priority_filter != "Todas" and classification.get("priority") != priority_filter:
                continue
            if category_filter != "Todas" and classification.get("category") != category_filter:
                continue
            if community_filter != "Todas" and item["incident"]["community_reference"] != community_filter:
                continue
            if date_filter != "Todas" and incident_date_key(item["incident"]["received_at"]) != date_filter:
                continue
            if contact_filter != "Todas" and item["incident"]["contact_name"] != contact_filter:
                continue
            filtered.append(item)

        filtered = sorted(
            filtered,
            key=lambda item: item["incident"]["received_at"],
            reverse=True,
        )

        rows = []
        for item in filtered:
            classification = get_effective_classification(item)
            rows.append(
                {
                    "Incidencia": public_refs[item["incident_id"]],
                    "Fecha": format_received_at(item["incident"]["received_at"]),
                    "Comunidad": item["incident"]["community_reference"],
                    "Categoría": category_label(classification["category"]),
                    "Prioridad": priority_label(classification["priority"]),
                    "Estado": operational_status_label(
                        canonical_operational_status(item.get("operational_status", "open"))
                    ),
                }
            )

        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No hay incidencias que coincidan con los filtros seleccionados.")
            return

        available_ids = [item["incident_id"] for item in filtered]
        current_selected = st.session_state.get("operational_selected_incident")
        if current_selected not in available_ids:
            current_selected = available_ids[0]

        selected_id = st.selectbox(
            "Selecciona una incidencia",
            available_ids,
            index=available_ids.index(current_selected),
            format_func=lambda incident_id: (
                f'{public_refs[incident_id]} · '
                f'{next(item for item in filtered if item["incident_id"] == incident_id)["incident"]["community_reference"]}'
            ),
            key="ops_incident_selector",
        )
        st.session_state["operational_selected_incident"] = selected_id
        selected = next(item for item in incidents if item["incident_id"] == selected_id)

    with st.expander("🕒 Seguimiento de la incidencia", expanded=False):
        render_operational_incident_detail(selected, public_refs[selected_id])


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">🏢 ComunIA</div>
            <div class="sidebar-brand-subtitle">
                Centro de control para triaje inteligente y supervisión humana.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-label">Modo de trabajo</div>', unsafe_allow_html=True)
    dashboard_mode = st.radio(
        "Modo de trabajo",
        ["Gestión de incidencias", "Supervisión IA"],
        label_visibility="collapsed",
        key="dashboard_mode",
    )

    st.markdown('<div class="sidebar-label">Estado del sistema</div>', unsafe_allow_html=True)
    try:
        health = api_request("GET", "/health")
        st.markdown(
            '<span class="status-pill online">● API conectada</span>',
            unsafe_allow_html=True,
        )
        st.caption(f'FastAPI · {health["status"]}')
    except RuntimeError as exc:
        st.markdown(
            '<span class="status-pill offline">● API sin conexión</span>',
            unsafe_allow_html=True,
        )
        st.caption(str(exc))

    if dashboard_mode == "Supervisión IA":
        st.markdown(
            """
            <div class="sidebar-panel">
                <div class="sidebar-label">Proveedores activos</div>
                <div class="sidebar-provider">🖥️ Ollama · Gemma 3 4B</div>
                <div class="sidebar-provider">☁️ Groq · Qwen 3.8 27B</div>
            </div>
            <div class="sidebar-panel">
                <div class="sidebar-label">Flujo de decisión IA</div>
                <div class="sidebar-provider">1 · Clasificación</div>
                <div class="sidebar-provider">2 · Comparación</div>
                <div class="sidebar-provider">3 · Validación humana</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-panel">
                <div class="sidebar-label">Flujo operativo</div>
                <div class="sidebar-provider">1 · Registro</div>
                <div class="sidebar-provider">2 · Seguimiento</div>
                <div class="sidebar-provider">3 · Resolución</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if dashboard_mode == "Gestión de incidencias":
    render_operational_dashboard()
    st.stop()


with st.expander("✉️ Nueva incidencia", expanded=False):
    render_section_header(
        "✉️",
        "Nueva incidencia",
        "Registra el aviso, selecciona un proveedor o compara ambos modelos sobre la misma entrada.",
    )

    with st.form("incident_form"):
        col_left, col_right = st.columns(2)

        with col_left:
            channel = st.selectbox(
                "Canal *",
                ["email", "whatsapp", "phone"],
                format_func=lambda value: CHANNEL_LABELS[value],
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
                max_chars=9,
                help="Introduce exactamente 9 cifras, sin espacios ni prefijos.",
            )
            provider = st.selectbox(
                "Proveedor para triaje",
                ["ollama", "groq"],
                format_func=lambda value: PROVIDER_LABELS[value],
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
    phone_error = phone_validation_message(contact_phone) if contact_phone.strip() else None


    if analyse:
        if missing_fields:
            st.error(
                "Debes completar los siguientes campos obligatorios: "
                + ", ".join(missing_fields)
            )
        elif phone_error:
            st.error(phone_error)
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
        elif phone_error:
            st.error(phone_error)
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
    render_section_header(
        "🧠",
        "Resultado del triaje",
        f'Comunidad identificada: {result["incident"]["community_reference"]}',
    )

    render_classification(result["classification"])
    render_metrics(result["metrics"])

    render_incident_review_feedback(result["incident_id"])
    render_incident_review_controls(
        result,
        key_prefix=f'current_triage_{result["incident_id"]}',
        show_heading=True,
    )


if "last_compare" in st.session_state:
    comparison = st.session_state["last_compare"]

    st.divider()
    render_section_header(
        "⚖️",
        "Comparación Ollama vs Groq",
        "Comparamos clasificación, rendimiento y calidad sobre la misma incidencia.",
    )
    st.markdown(
        '<div class="context-note">🏢 Comunidad identificada: '
        f'{escape(comparison["incident"]["community_reference"])}'
        '</div>',
        unsafe_allow_html=True,
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
            "Coincidencia entre modelos en categoría y prioridad. "
            "La validación humana confirma la calidad final."
        )
    else:
        st.warning(
            "Hay diferencias entre los modelos. "
            "La validación humana determinará la referencia correcta."
        )

    comparison_rows = []
    for provider_result in comparison["results"]:
        metrics = provider_result["metrics"]
        classification = provider_result["classification"]
        comparison_rows.append(
            {
                "Proveedor": PROVIDER_LABELS.get(metrics["provider"], metrics["provider"]),
                "Modelo": metrics["model"],
                "Categoría": category_label(classification["category"]),
                "Prioridad": priority_label(classification["priority"]),
                "Latencia": format_latency(metrics["latency_ms"]),
                "Tokens": metrics["input_tokens"] + metrics["output_tokens"],
                "Coste ref.": f'${metrics["estimated_cost"]:.6f}', 
            }
        )

    with st.container(border=True):
        st.markdown('<span class="opaque-work-card-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            '<div class="comparison-summary-title">Resumen comparativo</div>',
            unsafe_allow_html=True,
        )
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


with st.expander("🗂️ Histórico de incidencias", expanded=False):
    refresh_history = st.button(
        "Actualizar histórico",
        use_container_width=False,
    )

    if refresh_history or "incident_history" not in st.session_state:
        try:
            st.session_state["incident_history"] = api_request(
                "GET", "/incidents"
            )
        except RuntimeError as exc:
            st.error(str(exc))
            st.session_state["incident_history"] = []

    incidents = st.session_state.get("incident_history", [])

    if not incidents:
        st.info("Todavía no hay incidencias guardadas.")
    else:
        public_refs = build_public_incident_references(incidents)
        ordered_incidents = sorted(
            incidents,
            key=lambda item: item["incident"]["received_at"],
            reverse=True,
        )

        history_filter1, history_filter2 = st.columns(2)
        history_dates = sorted(
            {incident_date_key(item["incident"]["received_at"]) for item in ordered_incidents},
            reverse=True,
        )
        history_date_filter = history_filter1.selectbox(
            "Fecha",
            ["Todas", *history_dates],
            format_func=date_filter_label,
            key="supervision_incident_date_filter",
        )
        incidents_for_selected_date = [
            item for item in ordered_incidents
            if history_date_filter == "Todas"
            or incident_date_key(item["incident"]["received_at"]) == history_date_filter
        ]
        history_providers = sorted({item["metrics"]["provider"] for item in incidents_for_selected_date})
        history_provider_filter = history_filter2.selectbox(
            "Proveedor",
            ["Todos", *history_providers],
            format_func=lambda value: "Todos" if value == "Todos" else PROVIDER_LABELS.get(value, value),
            key="supervision_incident_provider_filter",
        )

        filtered_incidents = [
            item for item in incidents_for_selected_date
            if history_provider_filter == "Todos"
            or item["metrics"]["provider"] == history_provider_filter
        ]

        rows = []
        for item in filtered_incidents:
            effective = (
                item.get("human_classification")
                or item["classification"]
            )
            rows.append(
                {
                    "Incidencia": public_refs[item["incident_id"]],
                    "Fecha": format_received_at(
                        item["incident"]["received_at"]
                    ),
                    "Comunidad": item["incident"]["community_reference"],
                    "Categoría": category_label(effective["category"]),
                    "Prioridad": priority_label(effective["priority"]),
                    "Estado": status_label(item["human_status"]),
                    "Proveedor": PROVIDER_LABELS.get(
                        item["metrics"]["provider"],
                        item["metrics"]["provider"],
                    ),
                }
            )

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

        by_id = {item["incident_id"]: item for item in filtered_incidents}
        selected_id = st.selectbox(
            "Selecciona una incidencia para consultar sus datos",
            [item["incident_id"] for item in filtered_incidents],
            format_func=lambda incident_id: (
                f"{public_refs[incident_id]} · "
                f"{format_received_at(by_id[incident_id]['incident']['received_at'])} · "
                f"{PROVIDER_LABELS.get(by_id[incident_id]['metrics']['provider'], by_id[incident_id]['metrics']['provider'])} · "
                f"{by_id[incident_id]['incident']['community_reference']}"
            ),
            key="supervision_incident_history_selector",
        )

        selected = by_id[selected_id]
        effective = (
            selected.get("human_classification")
            or selected["classification"]
        )

        st.markdown(
            f"### 📄 {public_refs[selected_id]}"
        )
        detail_left, detail_right = st.columns(2)
        with detail_left:
            st.markdown(
                f"**Fecha:** {format_received_at(selected['incident']['received_at'])}"
            )
            st.markdown(
                f"**Comunidad:** {selected['incident']['community_reference']}"
            )
            st.markdown(
                f"**Vivienda / referencia:** {selected['incident']['property_reference']}"
            )
            st.markdown(
                f"**Canal:** {CHANNEL_LABELS.get(selected['incident']['channel'], selected['incident']['channel'])}"
            )
        with detail_right:
            st.markdown(
                f"**Persona de contacto:** {selected['incident']['contact_name']}"
            )
            st.markdown(
                f"**Teléfono:** {selected['incident']['contact_phone']}"
            )
            st.markdown(
                f"**Proveedor:** {PROVIDER_LABELS.get(selected['metrics']['provider'], selected['metrics']['provider'])}"
            )
            st.markdown(
                f"**Estado:** {status_label(selected['human_status'])}"
            )

        render_classification(effective)
        render_incident_review_feedback(selected_id)

        if selected.get("human_status") == "pending":
            st.warning(
                "Esta incidencia está pendiente de revisión humana. "
                "Puedes validarla ahora sin volver a registrar la incidencia."
            )
            if st.button(
                "👤 Validar incidencia ahora",
                key=f"open_history_review_{selected_id}",
                type="primary",
            ):
                st.session_state["history_review_open_for"] = selected_id

            if st.session_state.get("history_review_open_for") == selected_id:
                render_incident_review_controls(
                    selected,
                    key_prefix=f"history_review_{selected_id}",
                    show_heading=True,
                )
        elif st.session_state.get("history_review_open_for") == selected_id:
            st.session_state.pop("history_review_open_for", None)

        try:
            if "comparison_history" not in st.session_state:
                st.session_state["comparison_history"] = api_request(
                    "GET", "/comparisons"
                )
            selected_comparison = comparison_for_incident(
                st.session_state.get("comparison_history", []),
                selected_id,
            )
        except RuntimeError as exc:
            selected_comparison = None
            st.warning(
                "No se ha podido comprobar si existe una comparación: "
                f"{exc}"
            )

        if selected_comparison is None:
            st.info(
                "Esta incidencia todavía no se ha comparado con Ollama y Groq."
            )
            if st.button(
                "⚖️ Comparar Ollama vs Groq ahora",
                key=f"compare_history_incident_{selected_id}",
                type="primary",
            ):
                try:
                    with st.spinner(
                        "Comparando la incidencia con Ollama y Groq..."
                    ):
                        comparison = api_request(
                            "POST",
                            f"/incidents/{selected_id}/compare",
                        )
                    st.session_state["last_compare"] = comparison
                    st.session_state["comparison_history"] = api_request(
                        "GET", "/comparisons"
                    )
                    st.toast(
                        "Comparación Ollama vs Groq completada",
                        icon="⚖️",
                    )
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))
        else:
            st.success(
                "Esta incidencia ya dispone de comparación Ollama vs Groq. "
                "Puedes consultarla en el histórico de comparaciones y calidad."
            )

        st.caption(
            f"Identificador técnico interno: {selected['incident_id']}"
        )


with st.expander("📚 Histórico de comparaciones y calidad"):
    refresh_comparisons = st.button(
        "Actualizar histórico de comparaciones",
        use_container_width=False,
    )

    if (
        refresh_comparisons
        or "comparison_history" not in st.session_state
    ):
        try:
            st.session_state["comparison_history"] = api_request(
                "GET", "/comparisons"
            )
        except RuntimeError as exc:
            st.error(str(exc))
            st.session_state["comparison_history"] = []

    comparisons = st.session_state.get("comparison_history", [])

    if not comparisons:
        st.info("Todavía no hay comparaciones guardadas.")
    else:
        public_comparison_refs = build_public_comparison_references(
            comparisons
        )
        ordered_comparisons = sorted(
            comparisons,
            key=lambda item: item["incident"]["received_at"],
            reverse=True,
        )

        comparison_filter1, comparison_filter2 = st.columns(2)
        comparison_dates = sorted(
            {incident_date_key(item["incident"]["received_at"]) for item in ordered_comparisons},
            reverse=True,
        )
        comparison_date_filter = comparison_filter1.selectbox(
            "Fecha",
            ["Todas", *comparison_dates],
            format_func=date_filter_label,
            key="comparison_history_date_filter",
        )
        comparison_provider_filter = comparison_filter2.selectbox(
            "Proveedor a consultar",
            ["Todos", "ollama", "groq"],
            format_func=lambda value: "Todos" if value == "Todos" else PROVIDER_LABELS[value],
            key="comparison_history_provider_filter",
        )

        filtered_comparisons = [
            item for item in ordered_comparisons
            if comparison_date_filter == "Todas"
            or incident_date_key(item["incident"]["received_at"]) == comparison_date_filter
        ]

        rows = []
        for item in filtered_comparisons:
            review = item.get("human_review")
            by_provider = {
                result["metrics"]["provider"]: result
                for result in item["results"]
            }
            base_row = {
                "Comparación": public_comparison_refs[item["incident_id"]],
                "Fecha": format_received_at(item["incident"]["received_at"]),
                "Comunidad": item["incident"]["community_reference"],
                "Validación humana": "Sí" if review else "Pendiente",
            }
            if comparison_provider_filter == "Todos":
                base_row.update(
                    {
                        "Ollama · categoría": category_label(by_provider["ollama"]["classification"]["category"]),
                        "Groq · categoría": category_label(by_provider["groq"]["classification"]["category"]),
                        "Ollama · prioridad": priority_label(by_provider["ollama"]["classification"]["priority"]),
                        "Groq · prioridad": priority_label(by_provider["groq"]["classification"]["priority"]),
                    }
                )
            else:
                provider_result = by_provider[comparison_provider_filter]
                base_row.update(
                    {
                        "Proveedor": PROVIDER_LABELS[comparison_provider_filter],
                        "Categoría": category_label(provider_result["classification"]["category"]),
                        "Prioridad": priority_label(provider_result["classification"]["priority"]),
                        "Latencia": format_latency(provider_result["metrics"]["latency_ms"]),
                    }
                )
            rows.append(base_row)

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

        comparisons_by_id = {
            item["incident_id"]: item
            for item in filtered_comparisons
        }
        provider_selector_label = (
            "Ollama + Groq"
            if comparison_provider_filter == "Todos"
            else PROVIDER_LABELS[comparison_provider_filter]
        )
        selected_comparison_id = st.selectbox(
            "Selecciona una comparación para consultar sus datos",
            [item["incident_id"] for item in filtered_comparisons],
            format_func=lambda comparison_id: (
                f"{public_comparison_refs[comparison_id]} · "
                f"{format_received_at(comparisons_by_id[comparison_id]['incident']['received_at'])} · "
                f"{provider_selector_label} · "
                f"{comparisons_by_id[comparison_id]['incident']['community_reference']}"
            ),
            key="comparison_history_selector",
        )

        selected_comparison = comparisons_by_id[
            selected_comparison_id
        ]
        st.markdown(
            f"### 📊 {public_comparison_refs[selected_comparison_id]}"
        )
        st.caption(
            f"{format_received_at(selected_comparison['incident']['received_at'])}"
            f" · {selected_comparison['incident']['community_reference']}"
        )

        visible_results = selected_comparison["results"]
        if comparison_provider_filter != "Todos":
            visible_results = [
                result for result in visible_results
                if result["metrics"]["provider"] == comparison_provider_filter
            ]

        provider_columns = st.columns(len(visible_results))
        for column, provider_result in zip(
            provider_columns,
            visible_results,
            strict=True,
        ):
            with column:
                render_provider_comparison_card(provider_result)

        review = selected_comparison.get("human_review")
        if review:
            st.markdown("**👤 Referencia humana guardada**")
            human_left, human_mid, human_right = st.columns(3)
            human_left.metric(
                "Categoría correcta",
                category_label(review["reference_category"]),
            )
            human_mid.metric(
                "Prioridad correcta",
                priority_label(review["reference_priority"]),
            )
            human_right.metric(
                "Valoración",
                PREFERENCE_LABELS.get(
                    review["preferred_result"],
                    review["preferred_result"],
                ),
            )
        else:
            st.info(
                "Esta comparación todavía no tiene validación humana."
            )

        try:
            quality_summary = api_request("GET", "/comparisons/quality")
            render_quality_summary(quality_summary)
        except RuntimeError as exc:
            st.warning(
                "No se pudo cargar la calidad acumulada: "
                f"{exc}"
            )


st.markdown(
    """
    <div class="comunia-footer">
        <strong>ComunIA</strong> · FastAPI + Pydantic + Ollama + Groq + Streamlit ·
        Diseño orientado a supervisión humana y trazabilidad.<br>
        Fondo: <a href="https://unsplash.com/photos/modern-apartment-buildings-with-a-green-courtyard-8Li3kSPoeo4" target="_blank">Corentin Jaunault / Unsplash</a>
        · uso gratuito bajo Unsplash License.
    </div>
    """,
    unsafe_allow_html=True,
)

