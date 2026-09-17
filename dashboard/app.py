"""Dashboard Streamlit de ComunIA."""

from collections import defaultdict
from datetime import datetime
from html import escape
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
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


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


def render_hero() -> None:
    """Cabecera de producto: identidad, propósito y pilares técnicos."""

    st.markdown(
        """
        <section class="comunia-hero">
            <div class="hero-kicker">🌿 IA aplicada a la gestión residencial</div>
            <h1 class="hero-title">Comun<span class="accent">IA</span></h1>
            <p class="hero-subtitle">
                Motor inteligente de triaje para comunidades de propietarios.
                Clasifica incidencias, compara modelos y mantiene la decisión
                final bajo supervisión humana.
            </p>
            <div class="hero-tags">
                <span class="hero-tag">🛡️ API Type-Safe</span>
                <span class="hero-tag">🖥️ Ollama local</span>
                <span class="hero-tag">☁️ Groq externo</span>
                <span class="hero-tag">👤 Human-in-the-loop</span>
                <span class="hero-tag">📊 Calidad medible</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(icon: str, title: str, subtitle: str) -> None:
    """Cabecera consistente para cada bloque funcional del dashboard."""

    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-icon">{icon}</div>
            <div class="section-copy">
                <h2>{title}</h2>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    with st.expander("🧠 Ver justificación auditable", expanded=True):
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
    """Tarjeta visual de proveedor con clasificación y rendimiento."""

    metrics = provider_result["metrics"]
    classification = provider_result["classification"]
    provider = metrics["provider"]
    chip_class = "local" if provider == "ollama" else "external"
    priority = classification["priority"]

    with st.container(border=True):
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
        st.caption("Modelo utilizado en esta inferencia")

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

        with st.expander("🧠 Justificación del modelo"):
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
        "La supervisión humana fija la referencia correcta y permite medir el acierto real de cada modelo.",
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
        "Métricas calculadas únicamente sobre comparaciones validadas por una persona supervisora.",
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

    st.markdown(
        """
        <div class="sidebar-panel">
            <div class="sidebar-label">Proveedores activos</div>
            <div class="sidebar-provider">🖥️ Ollama · Gemma 3 4B</div>
            <div class="sidebar-provider">☁️ Groq · Qwen 3.8 27B</div>
        </div>
        <div class="sidebar-panel">
            <div class="sidebar-label">Flujo de decisión</div>
            <div class="sidebar-provider">1 · Recepción</div>
            <div class="sidebar-provider">2 · Clasificación IA</div>
            <div class="sidebar-provider">3 · Validación humana</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    render_section_header(
        "🧠",
        "Resultado del triaje",
        f'Comunidad identificada: {result["incident"]["community_reference"]}',
    )

    render_classification(result["classification"])
    render_metrics(result["metrics"])

    render_section_header(
        "✅",
        "Validación humana",
        "Aprueba la propuesta del modelo o corrige la clasificación antes del registro final.",
    )

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
                format_func=category_label,
            )
            corrected_priority = st.selectbox(
                "Prioridad",
                [item.value for item in Priority],
                index=[item.value for item in Priority].index(
                    current["priority"]
                ),
                format_func=priority_label,
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
                format_func=area_label,
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

    st.caption(f'Estado de revisión: {status_label(result["human_status"])}')


if "last_compare" in st.session_state:
    comparison = st.session_state["last_compare"]

    st.divider()
    render_section_header(
        "⚖️",
        "Comparación Ollama vs Groq",
        "Misma incidencia y mismo contrato Pydantic: comparamos clasificación, latencia, tokens, coste y calidad.",
    )
    st.caption(
        f'🏢 Comunidad identificada: '
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
                "categoría": category_label(classification["category"]),
                "prioridad": priority_label(classification["priority"]),
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

        rows = []
        for item in ordered_incidents:
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

        by_id = {item["incident_id"]: item for item in ordered_incidents}
        selected_id = st.selectbox(
            "Selecciona una incidencia para consultar sus datos",
            [item["incident_id"] for item in ordered_incidents],
            format_func=lambda incident_id: (
                f"{public_refs[incident_id]} · "
                f"{format_received_at(by_id[incident_id]['incident']['received_at'])} · "
                f"{by_id[incident_id]['incident']['community_reference']}"
            ),
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

        rows = []
        for item in ordered_comparisons:
            review = item.get("human_review")
            by_provider = {
                result["metrics"]["provider"]: result
                for result in item["results"]
            }
            rows.append(
                {
                    "Comparación": public_comparison_refs[
                        item["incident_id"]
                    ],
                    "Fecha": format_received_at(
                        item["incident"]["received_at"]
                    ),
                    "Comunidad": item["incident"][
                        "community_reference"
                    ],
                    "Ollama · categoría": category_label(
                        by_provider["ollama"]["classification"]["category"]
                    ),
                    "Groq · categoría": category_label(
                        by_provider["groq"]["classification"]["category"]
                    ),
                    "Ollama · prioridad": priority_label(
                        by_provider["ollama"]["classification"]["priority"]
                    ),
                    "Groq · prioridad": priority_label(
                        by_provider["groq"]["classification"]["priority"]
                    ),
                    "Validación humana": "Sí" if review else "Pendiente",
                }
            )

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

        comparisons_by_id = {
            item["incident_id"]: item
            for item in ordered_comparisons
        }
        selected_comparison_id = st.selectbox(
            "Selecciona una comparación para consultar sus datos",
            [item["incident_id"] for item in ordered_comparisons],
            format_func=lambda comparison_id: (
                f"{public_comparison_refs[comparison_id]} · "
                f"{format_received_at(comparisons_by_id[comparison_id]['incident']['received_at'])} · "
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

        provider_columns = st.columns(2)
        for column, provider_result in zip(
            provider_columns,
            selected_comparison["results"],
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

