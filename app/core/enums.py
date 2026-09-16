"""Enumeraciones compartidas por ComunIA.

Centralizar estos valores evita inconsistencias como "Alta", "ALTA" o "alta"
y ayuda a que Pydantic pueda validar entradas y salidas de forma estricta.
"""

from enum import Enum


class Channel(str, Enum):
    """Canal por el que se recibe una incidencia."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PHONE = "phone"


class Priority(str, Enum):
    """Nivel de prioridad propuesto para una incidencia."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    """Categorías funcionales admitidas por el motor de triaje."""

    ASCENSORES = "ascensores"
    FONTANERIA = "fontaneria"
    DANOS_AGUA = "danos_agua"
    ELECTRICIDAD = "electricidad"
    ANTENA_TV = "antena_tv"
    PORTERO_AUTOMATICO = "portero_automatico"
    PLAGAS = "plagas"
    JARDIN = "jardin"
    PISCINA = "piscina"
    SEGURIDAD = "seguridad"
    LIMPIEZA = "limpieza"
    ZONAS_COMUNES = "zonas_comunes"
    GARAJE = "garaje"
    CONVIVENCIA = "convivencia"
    ADMINISTRACION = "administracion"
    CONTABILIDAD = "contabilidad"
    OBRAS = "obras"
    OTROS = "otros"


class ResponsibleArea(str, Enum):
    """Áreas internas a las que ComunIA puede derivar una incidencia."""

    MANTENIMIENTO = "mantenimiento"
    GESTION_COMUNIDAD = "gestion_comunidad"


class LLMProvider(str, Enum):
    """Proveedores LLM disponibles."""

    OLLAMA = "ollama"
    OPENAI = "openai"


class HumanReviewStatus(str, Enum):
    """Estado de la revisión humana."""

    PENDING = "pending"
    APPROVED = "approved"
    CORRECTED = "corrected"
