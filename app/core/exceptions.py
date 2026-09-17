"""Excepciones controladas de ComunIA."""


class ComunIAError(Exception):
    """Error base de la aplicación."""


class LLMProviderError(ComunIAError):
    """Error general al comunicarse con un proveedor LLM."""


class LLMTransientError(LLMProviderError):
    """Error temporal que puede resolverse mediante reintento."""


class LLMRateLimitError(LLMTransientError):
    """El proveedor ha aplicado un rate limit."""


class LLMConfigurationError(LLMProviderError):
    """Falta configuración necesaria para usar un proveedor."""


class InvalidLLMResponseError(ComunIAError):
    """La respuesta del LLM no cumple el contrato Pydantic."""


class PersistenceError(ComunIAError):
    """No se ha podido leer o escribir el almacenamiento local."""


class IncidentNotFoundError(PersistenceError):
    """No existe la incidencia solicitada."""


class ComparisonNotFoundError(PersistenceError):
    """No existe la comparación solicitada."""
