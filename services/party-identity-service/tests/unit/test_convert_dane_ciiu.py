"""Conversor del archivo oficial del DANE a CSV del `seed` CIIU (T064, R-10)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ciiu" / "convert_dane_ciiu.py"
_spec = importlib.util.spec_from_file_location("convert_dane_ciiu", SCRIPT)
convert = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert)

HEADER = ("Categoría", "CIIU Rev. 5 A.C. Código, incluida la sección", "CIIU Rev 5 A.C. Código",
          "CIIU Rev 5 A.C. Título")
ROWS = [
    (None, None, None, "Clasificación Industrial ... (CIIU Rev. 5 A.C.)"),
    HEADER,
    ("Sección", "A", "A", "Agricultura, ganadería, caza, silvicultura y pesca"),
    ("División", "A01", "01", "Agricultura, ganadería, caza y actividades de servicios conexas"),
    ("Grupo", "A011", "011", "Cultivos agrícolas transitorios"),
    ("Clase", "A0111", "0111", "Cultivo de cereales (excepto arroz), legumbres y semillas oleaginosas"),
    ("Sección", "B", "B", "Explotación de minas y canteras"),
    ("División", "B05", "05", "Extracción de carbón de piedra y lignito"),
]


def _by_code(rows):
    return {row["code"]: row for row in rows}


def test_hierarchy_is_derived_from_codes() -> None:
    rows = _by_code(convert.derive_rows(ROWS))

    assert rows["A"] == {"level": "SECTION", "code": "A", "name": ROWS[2][3], "parent_code": ""}
    assert rows["01"]["level"] == "DIVISION" and rows["01"]["parent_code"] == "A"
    assert rows["011"]["level"] == "GROUP" and rows["011"]["parent_code"] == "01"
    assert rows["0111"]["level"] == "CLASS" and rows["0111"]["parent_code"] == "011"
    assert rows["05"]["parent_code"] == "B"


def test_rows_before_header_and_blank_rows_are_ignored() -> None:
    rows = convert.derive_rows([*ROWS, (None, None, None, None)])

    assert [row["code"] for row in rows] == ["A", "01", "011", "0111", "B", "05"]


def test_names_are_kept_exactly_but_trimmed() -> None:
    rows = convert.derive_rows([HEADER, ("Sección", "A", "A", "  Agricultura  ")])

    assert rows[0]["name"] == "Agricultura"


@pytest.mark.parametrize(
    "row, message",
    [
        (("Subclase", "A01111", "01111", "x"), "Categoría desconocida"),
        (("División", "A01", "011", "x"), "longitud"),
        (("División", "A02", "01", "x"), "no coincide"),
        (("Grupo", "A019", "019", "x"), "padre"),
        (("Sección", "A", "A", ""), "título"),
    ],
)
def test_invalid_rows_fail(row, message) -> None:
    rows = [HEADER, ("Sección", "A", "A", "Agricultura"), row]

    with pytest.raises(ValueError, match=message):
        convert.derive_rows(rows)


def test_duplicated_code_fails() -> None:
    rows = [HEADER, ("Sección", "A", "A", "Agricultura"), ("Sección", "A", "A", "Otra")]

    with pytest.raises(ValueError, match="duplicado"):
        convert.derive_rows(rows)


def test_missing_header_fails() -> None:
    with pytest.raises(ValueError, match="encabezado"):
        convert.derive_rows([("Sección", "A", "A", "Agricultura")])


def test_csv_is_deterministic_with_lf(tmp_path) -> None:
    rows = convert.derive_rows(ROWS)
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"

    convert.write_csv(rows, first)
    convert.write_csv(rows, second)

    content = first.read_bytes()
    assert content == second.read_bytes()
    assert b"\r\n" not in content
    assert content.splitlines()[0] == b"level,code,name,parent_code"
