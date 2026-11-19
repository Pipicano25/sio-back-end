"""Dígito de verificación del NIT (módulo 11 de la DIAN, enmienda DS-13 del 2026-11-18).

Pruebas sin base de datos: el cálculo, la validación del formato y su uso dentro de
`match_identification_number` con la regla `NIT` de Colombia.
"""

from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    InvalidIdentificationNumberError,
    UnsupportedIdentificationTypeError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
    match_identification_number,
    nit_check_digit,
    validate_nit_check_digit,
)

NIT_PATTERN = "^[0-9]{6,10}-[0-9]$"


def _rule(sigla: str = "NIT", pattern: str = NIT_PATTERN) -> IdentificationRule:
    return IdentificationRule(
        party_kind="ORGANIZATION",
        country_id=uuid4(),
        identification_type="TAX_ID",
        sigla=sigla,
        pattern=pattern,
        description="Numero de Identificacion Tributaria de organizacion.",
    )


# NIT reales de organizaciones registradas en el entorno local (todas con el dígito del RUT).
REAL_NITS = [
    "817004260-0",  # GRUPO DAO S.A.S.
    "890300466-5",  # TECNOQUIMICAS S A
    "830105173-9",  # CDE LABORATORIOS S A S
    "860078781-1",  # FARMACOL CHINOIN S A S
    "890106527-5",  # PROCAPS S A
    "800013834-4",  # LABORATORIOS LA SANTÉ S A
    "900441048-1",  # EUROFARMA COLOMBIA S A S
    "811000967-9",  # LABORATORIOS LICOL S A S
]


@pytest.mark.parametrize("nit", REAL_NITS)
def test_real_nits_have_the_computed_digit(nit: str) -> None:
    base, digit = nit.split("-")

    assert nit_check_digit(base) == int(digit)


@pytest.mark.parametrize(
    ("base", "remainder_case", "digit"),
    [
        ("900123456", "residuo 3 → 11 − 3", 8),
        ("800000123", "residuo 1 → 1", 1),
        ("00000000", "residuo 0 → 0", 0),
    ],
)
def test_remainder_zero_or_one_is_the_digit_otherwise_eleven_minus(base, remainder_case, digit) -> None:
    assert nit_check_digit(base) == digit, remainder_case


def test_weights_go_from_right_to_left() -> None:
    # 1 en la posición de las unidades pesa 3; en las decenas pesa 7.
    assert nit_check_digit("1") == 11 - 3
    assert nit_check_digit("10") == 11 - 7


@pytest.mark.parametrize("nit", REAL_NITS)
def test_validate_accepts_correct_digit(nit: str) -> None:
    validate_nit_check_digit(nit)


def test_validate_rejects_wrong_digit_and_says_which_was_expected() -> None:
    with pytest.raises(InvalidIdentificationNumberError) as error:
        validate_nit_check_digit("817004260-5")

    assert "para la base 817004260 corresponde 0, no 5" in error.value.message


@pytest.mark.parametrize("number", ["GENERICO-0", "90012A456-8", "900123456", "900123456-"])
def test_validate_rejects_non_numeric_format(number: str) -> None:
    with pytest.raises(InvalidIdentificationNumberError):
        validate_nit_check_digit(number)


def test_match_accepts_valid_nit() -> None:
    rule = _rule()

    assert match_identification_number([rule], "817004260-0", sigla="NIT") == [rule]


@pytest.mark.parametrize(
    "number",
    [
        "817004260-5",  # dígito incorrecto
        "GENERICO-0",  # letras
        "12345-1",  # base de 5 dígitos
        "12345678901-1",  # base de 11 dígitos
    ],
)
def test_match_rejects_invalid_nit(number: str) -> None:
    with pytest.raises(InvalidIdentificationNumberError):
        match_identification_number([_rule()], number, sigla="NIT")


def test_check_digit_is_only_applied_to_nit_rules() -> None:
    rule = _rule(sigla="CC", pattern="^[0-9]{3,10}-[0-9]$")

    assert match_identification_number([rule], "817004260-5", sigla="CC") == [rule]


def test_without_rules_the_sigla_is_unsupported_before_any_digit_check() -> None:
    with pytest.raises(UnsupportedIdentificationTypeError):
        match_identification_number([], "817004260-5", sigla="NIT")
