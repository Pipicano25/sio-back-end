"""Apoyo común de las pruebas de lectura por contrato de Business Reporting (spec 025).

BRS no tiene base propia: las bases de los propietarios (`business_reporting_test__<prop>`) se crean en el servidor
de la base de pruebas de Operational Context. La URL de administrador sale de `CONTRACT_TEST_ADMIN_URL` o, si
falta, de `OPERATIONAL_CONTEXT_TEST_DATABASE_URL` del `.env` de Operational Context, como su `conftest.py`. Sin
ninguna, las pruebas se omiten.

Los roles son del servidor: todas las bases de la corrida comparten `brs_contract_reader` y una sola contraseña.
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sio_auth.permissions import extract_permission_grants
from sio_auth.tokens import TokenClaims
from sqlalchemy.engine import make_url

SERVICES = Path(__file__).resolve().parents[3]
OC_OWNER = SERVICES / "operational-context-service"


@pytest.fixture(scope="session")
def contract_admin_url() -> str:
    url = os.environ.get("CONTRACT_TEST_ADMIN_URL", "").strip()
    if not url:
        # Sin `load_dotenv`: no debe dejar variables de Operational Context en el entorno de las demás pruebas.
        from dotenv import dotenv_values

        url = (dotenv_values(OC_OWNER / ".env").get("OPERATIONAL_CONTEXT_TEST_DATABASE_URL") or "").strip()
    if not url:
        pytest.skip("Sin URL de una base de pruebas de Operational Context.")
    if "test" not in (make_url(url).database or ""):
        pytest.fail("La URL de administrador debe ser de una base de pruebas.")
    return url


@pytest.fixture(scope="session")
def reader_password() -> str:
    return secrets.token_urlsafe(24)


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject, issuer="test", audiences=("sio-api",), expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles), permissions=extract_permission_grants(roles), preferred_username=None, email=None,
        raw={},
    )
