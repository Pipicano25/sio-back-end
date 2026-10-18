"""Aplicación de las pruebas de API con los dobles de OC, CR, PC e Inventory inyectados (Principio IV)."""

from __future__ import annotations

import pytest

from product_inventory_query_service.application.listing import Ports
from product_inventory_query_service.main import create_app
from tests.api.support import World
from tests.fakes import build_fakes


@pytest.fixture
def fakes():
    return build_fakes()


@pytest.fixture
def authorizations() -> list:
    """Cabeceras `Authorization` con que se construyó el puerto de OC en cada solicitud."""
    return []


@pytest.fixture
def ports_factory(fakes, authorizations):
    def factory(authorization):
        authorizations.append(authorization)
        return Ports(fakes.oc, fakes.cr, fakes.pc, fakes.inventory)

    return factory


@pytest.fixture
def app(test_settings, test_auth, jwks_state, ports_factory):
    return create_app(test_settings, auth=test_auth, jwks_probe=lambda: jwks_state["available"],
                      ports_factory=ports_factory)


@pytest.fixture
def world(fakes) -> World:
    return World.create(fakes)
