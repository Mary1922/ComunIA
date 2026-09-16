"""Tests del matching tolerante de comunidades."""

import json

import pytest

from app.services.community_service import (
    CommunityNotFoundError,
    CommunityService,
)


@pytest.fixture
def service(tmp_path):
    path = tmp_path / "communities.json"
    path.write_text(
        json.dumps(
            [
                {"id": "COM-1", "name": "Avenida de la Democracia 110"},
                {"id": "COM-2", "name": "Avenida Pablo Neruda 11"},
                {"id": "COM-3", "name": "Avenida Pablo Neruda 14"},
            ]
        ),
        encoding="utf-8",
    )
    return CommunityService(path)


@pytest.mark.parametrize(
    "query",
    [
        "Av. Democracia 110",
        "AVDA DEMOCRACIA 110",
        "democracia 110",
        "Demcraci 110",
    ],
)
def test_variants_resolve_same_community(service, query):
    result = service.match(query)
    assert result.community_id == "COM-1"


def test_wrong_number_is_rejected(service):
    with pytest.raises(CommunityNotFoundError):
        service.match("Democracia 999")
