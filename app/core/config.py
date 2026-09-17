"""Configuración centralizada de ComunIA."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Variables configurables de la aplicación.

    Los secretos reales se leen desde .env y nunca deben subirse a GitHub.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ComunIA"
    app_version: str = "1.0.0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3"

    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "qwen/qwen3.8-27b"

    # Tarifa publicada de referencia por millón de tokens.
    # El proyecto puede funcionar en Groq Free tier sin coste facturado,
    # pero mantenemos esta estimación para comparar proveedores en la rúbrica.
    groq_input_cost_per_1m: float = Field(default=0.80, ge=0)
    groq_output_cost_per_1m: float = Field(default=4.00, ge=0)

    temperature: float = Field(default=0.1, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)

    request_timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=1, le=6)
    max_repair_attempts: int = Field(default=2, ge=0, le=4)

    incidents_path: Path = PROJECT_ROOT / "data" / "incidents.json"
    comparisons_path: Path = PROJECT_ROOT / "data" / "comparisons.json"
    communities_path: Path = PROJECT_ROOT / "data" / "communities.json"


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia reutilizable de Settings."""

    return Settings()
