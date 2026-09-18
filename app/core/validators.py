"""Validadores reutilizables de dominio para ComunIA."""

import re


SPANISH_PHONE_RE = re.compile(r"^\d{9}$")


def is_valid_spanish_phone(value: str) -> bool:
    """Comprueba que el teléfono tenga exactamente 9 cifras numéricas."""

    return bool(SPANISH_PHONE_RE.fullmatch(value.strip()))


def normalize_spanish_phone(value: str) -> str:
    """Valida y devuelve el teléfono normalizado.

    Para este proyecto se exige el formato nacional español: exactamente
    9 cifras, sin espacios, prefijos internacionales ni separadores.
    """

    normalized = value.strip()
    if not is_valid_spanish_phone(normalized):
        raise ValueError(
            "El teléfono debe contener exactamente 9 cifras y solo números."
        )
    return normalized
