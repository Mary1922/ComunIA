"""Resolución tolerante de comunidades a partir de texto libre."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata

from rapidfuzz import fuzz

from app.models.schemas import CommunityMatchResult, CommunityRecord


ROAD_TYPE_TOKENS = {
    "avenida",
    "av",
    "avda",
    "calle",
    "c",
    "cl",
    "paseo",
    "ps",
    "plaza",
    "pza",
}

STOPWORDS = {"de", "del", "la", "las", "los", "el"}


class CommunityMatchError(ValueError):
    """Error base al intentar identificar una comunidad."""


class CommunityNumberMissingError(CommunityMatchError):
    """La referencia no contiene número de finca."""


class CommunityNotFoundError(CommunityMatchError):
    """No existe una coincidencia suficientemente fiable."""


class AmbiguousCommunityError(CommunityMatchError):
    """Existen varias coincidencias demasiado próximas."""


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    )


def _basic_normalize(value: str) -> str:
    value = _strip_accents(value.lower())
    value = re.sub(r"\b(nº|n°|numero|num)\b", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def _extract_street_number(value: str) -> str | None:
    """Toma el último número, útil para vías como 'Avenida 2 de Mayo 14'."""

    normalized = _basic_normalize(value)
    numbers = re.findall(r"\b\d+[a-z]?\b", normalized)
    return numbers[-1] if numbers else None


def _normalize_street_name(value: str) -> str:
    normalized = _basic_normalize(value)
    number = _extract_street_number(normalized)

    cleaned_tokens = [
        token
        for token in normalized.split()
        if token != number
        and token not in ROAD_TYPE_TOKENS
        and token not in STOPWORDS
    ]
    return " ".join(cleaned_tokens)


class CommunityService:
    """Busca una comunidad real a partir de una referencia libre."""

    def __init__(
        self,
        communities_path: Path | str,
        minimum_score: float = 72.0,
        ambiguity_margin: float = 5.0,
    ) -> None:
        self.communities_path = Path(communities_path)
        self.minimum_score = minimum_score
        self.ambiguity_margin = ambiguity_margin
        self._communities = self._load_communities()

    def _load_communities(self) -> list[CommunityRecord]:
        try:
            raw_data = json.loads(
                self.communities_path.read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"No se encuentra el catálogo: {self.communities_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "communities.json no contiene JSON válido."
            ) from exc

        if not isinstance(raw_data, list):
            raise RuntimeError(
                "communities.json debe contener una lista."
            )

        communities = [
            CommunityRecord.model_validate(item)
            for item in raw_data
        ]

        if not communities:
            raise RuntimeError("El catálogo de comunidades está vacío.")

        ids = [item.id for item in communities]
        if len(ids) != len(set(ids)):
            raise RuntimeError(
                "Existen identificadores de comunidad duplicados."
            )

        return communities

    def match(self, community_reference: str) -> CommunityMatchResult:
        query_number = _extract_street_number(community_reference)

        if query_number is None:
            raise CommunityNumberMissingError(
                "Indica el nombre de la calle y el número de la comunidad."
            )

        query_street = _normalize_street_name(community_reference)

        if len(query_street) < 3:
            raise CommunityNotFoundError(
                "No hemos podido identificar la calle. "
                "Escribe el nombre de la vía y el número."
            )

        candidates = [
            community
            for community in self._communities
            if _extract_street_number(community.name) == query_number
        ]

        if not candidates:
            raise CommunityNotFoundError(
                "No hemos encontrado ninguna comunidad con ese número. "
                "Comprueba la calle y el número e inténtalo de nuevo."
            )

        scored_candidates = []
        for community in candidates:
            candidate_street = _normalize_street_name(community.name)
            score = float(fuzz.WRatio(query_street, candidate_street))
            scored_candidates.append((community, score))

        scored_candidates.sort(key=lambda item: item[1], reverse=True)
        best_community, best_score = scored_candidates[0]

        if best_score < self.minimum_score:
            raise CommunityNotFoundError(
                "No hemos podido identificar la comunidad con suficiente "
                "seguridad. Comprueba la calle y el número."
            )

        if len(scored_candidates) > 1:
            _, second_score = scored_candidates[1]
            if (
                second_score >= self.minimum_score
                and best_score - second_score <= self.ambiguity_margin
            ):
                raise AmbiguousCommunityError(
                    "La referencia coincide con más de una comunidad. "
                    "Escribe el nombre de la calle con más detalle."
                )

        return CommunityMatchResult(
            query=community_reference,
            community_id=best_community.id,
            canonical_name=best_community.name,
            score=round(best_score, 1),
        )
