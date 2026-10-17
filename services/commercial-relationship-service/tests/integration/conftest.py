"""Integración real: antes de la primera prueba, todos los destinos deben ser la pila aislada `sio-it-*`.

La barrera (`validation/isolation_guard.py`) exige `SIO_TEST_TARGET=isolated` y que cada puerto pertenezca a un
contenedor con `sio.integration.isolated=true`; si no, la sesión falla sin enviar ninguna solicitud (incidente del
2026-10-16).
"""

from __future__ import annotations

import pytest

from tests.integration.isolation import isolation_guard
from tests.integration.test_audit_delivery import AUDIT
from tests.integration.test_real_dependencies import (
    COMMERCIAL_RELATIONSHIP,
    GEOGRAPHY,
    OPERATIONAL_CONTEXT,
    PARTY_IDENTITY,
    PAYMENT_REFERENCE,
    PRODUCT_CATALOG,
    TOKEN_URL,
)


@pytest.fixture(scope="session", autouse=True)
def isolated_targets() -> None:
    isolation_guard().check_targets({
        "commercial_relationship": COMMERCIAL_RELATIONSHIP, "operational_context": OPERATIONAL_CONTEXT,
        "product_catalog": PRODUCT_CATALOG, "party_identity": PARTY_IDENTITY, "payment_reference": PAYMENT_REFERENCE,
        "geography": GEOGRAPHY, "audit": AUDIT, "keycloak": TOKEN_URL,
    })
