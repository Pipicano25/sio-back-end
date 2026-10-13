"""Forma del IUM (spec 018, FR-056b, DS-01, RC-IUM-1)."""

import pytest

from product_catalog_service.domain.ium import is_valid_ium


@pytest.mark.parametrize("value", ["2H1005971005105", "1A1023421000100", "3C1037861000100"])
def test_valid_ium(value: str) -> None:
    assert is_valid_ium(value)


@pytest.mark.parametrize(
    "value",
    [
        "ACTIVO",  # valor anómalo encontrado en la fuente oficial
        "1E100329100010",  # 14 caracteres
        "1F101287",  # truncado
        "M1037511000101",  # empieza con letra
        "2h1005971005105",  # minúscula: no se corrige
        "21H005971005105",  # letra fuera de la segunda posición
        "2HH005971005105",
        "",
    ],
)
def test_invalid_ium(value: str) -> None:
    assert not is_valid_ium(value)
