"""Endpoints REST de ComunIA."""

from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ComparisonNotFoundError,
    IncidentNotFoundError,
    InvalidLLMResponseError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    PersistenceError,
)
from app.models.schemas import (
    ComparisonQualitySummary,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonReviewRequest,
    HumanReviewRequest,
    TriageRequest,
    TriageResponse,
)
from app.services.community_service import (
    CommunityMatchError,
    CommunityService,
)
from app.services.comparison_repository import ComparisonRepository
from app.services.comparison_service import ComparisonService
from app.services.incident_repository import IncidentRepository
from app.services.triage_service import TriageService


router = APIRouter()


@lru_cache
def get_repository() -> IncidentRepository:
    settings = get_settings()
    return IncidentRepository(settings.incidents_path)


@lru_cache
def get_comparison_repository() -> ComparisonRepository:
    settings = get_settings()
    return ComparisonRepository(settings.comparisons_path)


@lru_cache
def get_community_service() -> CommunityService:
    settings = get_settings()
    return CommunityService(settings.communities_path)


@lru_cache
def get_triage_service() -> TriageService:
    settings: Settings = get_settings()
    return TriageService(
        settings=settings,
        community_service=get_community_service(),
        repository=get_repository(),
    )


@lru_cache
def get_comparison_service() -> ComparisonService:
    return ComparisonService(
        get_triage_service(),
        get_comparison_repository(),
    )


def _raise_controlled_http_error(exc: Exception) -> None:
    """Convierte errores de dominio en respuestas HTTP comprensibles."""

    if isinstance(exc, CommunityMatchError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if isinstance(exc, LLMConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if isinstance(exc, LLMRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El proveedor está temporalmente limitado. Inténtalo de nuevo.",
        ) from exc

    if isinstance(exc, InvalidLLMResponseError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "El modelo no ha conseguido devolver una clasificación válida "
                "después de los reintentos."
            ),
        ) from exc

    if isinstance(exc, LLMProviderError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if isinstance(exc, (IncidentNotFoundError, ComparisonNotFoundError)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, PersistenceError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al acceder al almacenamiento local.",
        ) from exc

    raise exc


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ComunIA"}


@router.post("/triage", response_model=TriageResponse)
async def triage(
    request: TriageRequest,
    service: TriageService = Depends(get_triage_service),
) -> TriageResponse:
    try:
        return await service.triage(request)
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.post("/compare", response_model=ComparisonResponse)
async def compare(
    request: ComparisonRequest,
    service: ComparisonService = Depends(get_comparison_service),
) -> ComparisonResponse:
    try:
        return await service.compare(request)
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.get("/incidents", response_model=list[TriageResponse])
async def list_incidents(
    repository: IncidentRepository = Depends(get_repository),
) -> list[TriageResponse]:
    try:
        return repository.list_all()
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.patch(
    "/incidents/{incident_id}/review",
    response_model=TriageResponse,
)
async def review_incident(
    incident_id: UUID,
    review: HumanReviewRequest,
    repository: IncidentRepository = Depends(get_repository),
) -> TriageResponse:
    try:
        return repository.apply_review(incident_id, review)
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.get("/comparisons", response_model=list[ComparisonResponse])
async def list_comparisons(
    repository: ComparisonRepository = Depends(get_comparison_repository),
) -> list[ComparisonResponse]:
    try:
        return repository.list_all()
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.get("/comparisons/quality", response_model=ComparisonQualitySummary)
async def comparison_quality(
    repository: ComparisonRepository = Depends(get_comparison_repository),
) -> ComparisonQualitySummary:
    try:
        return repository.quality_summary()
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise


@router.patch(
    "/comparisons/{comparison_id}/review",
    response_model=ComparisonResponse,
)
async def review_comparison(
    comparison_id: UUID,
    review: ComparisonReviewRequest,
    repository: ComparisonRepository = Depends(get_comparison_repository),
) -> ComparisonResponse:
    try:
        return repository.apply_review(comparison_id, review)
    except Exception as exc:
        _raise_controlled_http_error(exc)
        raise
