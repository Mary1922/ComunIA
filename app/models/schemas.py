"""Modelos Pydantic de entrada y salida de ComunIA."""

from datetime import datetime, timezone
import re
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.enums import (
    Category,
    Channel,
    ComparisonPreference,
    HumanReviewStatus,
    LLMProvider,
    Priority,
    ResponsibleArea,
)


CATEGORY_AREA_MAP: dict[Category, ResponsibleArea] = {
    Category.ASCENSORES: ResponsibleArea.MANTENIMIENTO,
    Category.FONTANERIA: ResponsibleArea.MANTENIMIENTO,
    Category.DANOS_AGUA: ResponsibleArea.MANTENIMIENTO,
    Category.ELECTRICIDAD: ResponsibleArea.MANTENIMIENTO,
    Category.ANTENA_TV: ResponsibleArea.MANTENIMIENTO,
    Category.PORTERO_AUTOMATICO: ResponsibleArea.MANTENIMIENTO,
    Category.PLAGAS: ResponsibleArea.MANTENIMIENTO,
    Category.JARDIN: ResponsibleArea.MANTENIMIENTO,
    Category.PISCINA: ResponsibleArea.MANTENIMIENTO,
    Category.LIMPIEZA: ResponsibleArea.MANTENIMIENTO,
    Category.GARAJE: ResponsibleArea.MANTENIMIENTO,
    Category.SEGURIDAD: ResponsibleArea.GESTION_COMUNIDAD,
    Category.ZONAS_COMUNES: ResponsibleArea.GESTION_COMUNIDAD,
    Category.CONVIVENCIA: ResponsibleArea.GESTION_COMUNIDAD,
    Category.ADMINISTRACION: ResponsibleArea.GESTION_COMUNIDAD,
    Category.CONTABILIDAD: ResponsibleArea.GESTION_COMUNIDAD,
    Category.OBRAS: ResponsibleArea.GESTION_COMUNIDAD,
    Category.OTROS: ResponsibleArea.GESTION_COMUNIDAD,
}


class ComunIABaseModel(BaseModel):
    """Configuración común de los modelos de la aplicación."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CommunityRecord(ComunIABaseModel):
    """Comunidad registrada en data/communities.json."""

    id: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=3, max_length=200)


class CommunityMatchResult(ComunIABaseModel):
    """Resultado de resolver la referencia libre de una comunidad."""

    query: str
    community_id: str
    canonical_name: str
    score: float = Field(ge=0, le=100)


class IncidentRequest(ComunIABaseModel):
    """Datos de una incidencia.

    Todos los campos identificativos son obligatorios.
    received_at se crea automáticamente si no llega en la petición.
    """

    text: str = Field(
        min_length=5,
        max_length=4000,
        description="Descripción de la incidencia.",
    )
    channel: Channel
    community_reference: str = Field(
        min_length=2,
        max_length=200,
        description=(
            "Texto libre con el que el usuario identifica la comunidad. "
            "La existencia real se comprueba después con CommunityService."
        ),
    )
    property_reference: str = Field(
        min_length=1,
        max_length=120,
        description="Vivienda, local, plaza o elemento del reportante.",
    )
    contact_name: str = Field(
        min_length=2,
        max_length=120,
        description="Persona que reporta la incidencia.",
    )
    contact_phone: str = Field(
        min_length=9,
        max_length=25,
        description="Teléfono de contacto.",
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha/hora de recepción; se genera si no se aporta.",
    )

    @field_validator("contact_phone")
    @classmethod
    def validate_and_normalize_phone(cls, value: str) -> str:
        """Acepta formatos habituales y almacena un teléfono normalizado."""

        normalized = re.sub(r"[\s().-]", "", value)

        if not re.fullmatch(r"\+?\d{9,15}", normalized):
            raise ValueError(
                "El teléfono debe contener entre 9 y 15 dígitos "
                "y puede comenzar por '+'."
            )

        return normalized

    @field_validator("received_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        """Evita fechas sin zona horaria."""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class TriageRequest(ComunIABaseModel):
    """Petición de triaje.

    El proveedor es una opción de ejecución, no un dato de la incidencia.
    """

    incident: IncidentRequest
    provider: LLMProvider


class ComparisonRequest(ComunIABaseModel):
    """Petición para comparar la misma incidencia con ambos proveedores."""

    incident: IncidentRequest


class TriageClassification(ComunIABaseModel):
    """Clasificación type-safe que debe producir el LLM."""

    category: Category
    priority: Priority
    summary: str = Field(
        min_length=1,
        max_length=250,
        description="Resumen de la incidencia en un máximo de 10 palabras.",
    )
    department: ResponsibleArea
    reasoning: str = Field(
        min_length=5,
        max_length=1000,
        description="Justificación breve y auditable de la clasificación.",
    )

    @field_validator("summary")
    @classmethod
    def validate_summary_word_count(cls, value: str) -> str:
        words = value.split()
        if len(words) > 10:
            raise ValueError(
                f"El resumen debe tener como máximo 10 palabras; "
                f"se recibieron {len(words)}."
            )
        return value

    @model_validator(mode="after")
    def validate_department_for_category(self):
        expected_area = CATEGORY_AREA_MAP[self.category]
        if self.department != expected_area:
            raise ValueError(
                f"La categoría '{self.category.value}' debe asignarse al área "
                f"'{expected_area.value}'."
            )
        return self


class ProviderMetrics(ComunIABaseModel):
    """Métricas acumuladas de una petición a un proveedor."""

    provider: LLMProvider
    model: str = Field(min_length=1, max_length=120)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)


class ProviderTriageResult(ComunIABaseModel):
    """Clasificación y métricas de un proveedor."""

    classification: TriageClassification
    metrics: ProviderMetrics


class TriageResponse(ComunIABaseModel):
    """Respuesta completa del endpoint /triage."""

    incident_id: UUID = Field(default_factory=uuid4)
    incident: IncidentRequest
    classification: TriageClassification
    metrics: ProviderMetrics
    human_status: HumanReviewStatus = HumanReviewStatus.PENDING
    human_classification: TriageClassification | None = None


class ProviderQualityAssessment(ComunIABaseModel):
    """Coincidencia de un proveedor con la referencia humana."""

    provider: LLMProvider
    category_correct: bool
    priority_correct: bool
    exact_match: bool
    quality_points: int = Field(ge=0, le=2)


class ComparisonReviewRequest(ComunIABaseModel):
    """Referencia humana usada para evaluar una comparación."""

    reference_category: Category
    reference_priority: Priority
    preferred_result: ComparisonPreference = ComparisonPreference.TIE
    notes: str | None = Field(default=None, max_length=1000)


class ComparisonHumanReview(ComparisonReviewRequest):
    """Validación humana ya aplicada, con evaluación por proveedor."""

    reviewed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    assessments: list[ProviderQualityAssessment] = Field(
        min_length=2,
        max_length=2,
    )

    @model_validator(mode="after")
    def ensure_two_provider_assessments(self):
        providers = {item.provider for item in self.assessments}
        if providers != {LLMProvider.OLLAMA, LLMProvider.GROQ}:
            raise ValueError(
                "La evaluación debe contener Ollama y Groq."
            )
        return self


class ComparisonResponse(ComunIABaseModel):
    """Respuesta persistida del endpoint /compare."""

    incident_id: UUID = Field(default_factory=uuid4)
    incident: IncidentRequest
    results: list[ProviderTriageResult] = Field(min_length=2, max_length=2)
    human_review: ComparisonHumanReview | None = None

    @model_validator(mode="after")
    def ensure_two_different_providers(self):
        providers = {result.metrics.provider for result in self.results}
        if providers != {LLMProvider.OLLAMA, LLMProvider.GROQ}:
            raise ValueError(
                "La comparación debe contener un resultado de Ollama "
                "y otro de Groq."
            )
        return self


class ProviderQualitySummary(ComunIABaseModel):
    """Métricas agregadas de calidad y rendimiento de un proveedor."""

    provider: LLMProvider
    comparisons: int = Field(ge=0)
    reviewed: int = Field(ge=0)
    category_accuracy_pct: float | None = Field(default=None, ge=0, le=100)
    priority_accuracy_pct: float | None = Field(default=None, ge=0, le=100)
    exact_match_rate_pct: float | None = Field(default=None, ge=0, le=100)
    preferred_count: int = Field(ge=0)
    average_latency_ms: float | None = Field(default=None, ge=0)
    total_estimated_cost: float = Field(ge=0)


class ComparisonQualitySummary(ComunIABaseModel):
    """Resumen acumulado de comparaciones y validaciones humanas."""

    total_comparisons: int = Field(ge=0)
    reviewed_comparisons: int = Field(ge=0)
    providers: list[ProviderQualitySummary] = Field(min_length=2, max_length=2)


class HumanReviewRequest(ComunIABaseModel):
    """Validación humana de una clasificación individual."""

    status: HumanReviewStatus
    classification: TriageClassification | None = None

    @model_validator(mode="after")
    def validate_review(self):
        if self.status == HumanReviewStatus.PENDING:
            raise ValueError("Una revisión no puede volver al estado pending.")

        if (
            self.status == HumanReviewStatus.CORRECTED
            and self.classification is None
        ):
            raise ValueError(
                "Una revisión corrected debe incluir la clasificación corregida."
            )

        if (
            self.status == HumanReviewStatus.APPROVED
            and self.classification is not None
        ):
            raise ValueError(
                "Una revisión approved no debe incluir otra clasificación."
            )

        return self
