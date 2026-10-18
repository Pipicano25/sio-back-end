"""Toda ruta bajo `/api/v1` exige autenticación y permiso (RC-12, Principio XIII).

La prueba recorre las rutas registradas, por lo que cubre automáticamente las
que agregue cada historia.
"""

import re
from uuid import uuid4

import pytest

from product_catalog_service.main import create_app

_PARAM = re.compile(r"\{[^}]+\}")


def _protected_routes():
    schema = create_app().openapi()
    for path, operations in schema["paths"].items():
        if not path.startswith("/api/v1") or path.startswith("/api/v1/public/"):
            # Spec 022: la ruta pública exacta de imágenes no exige token (test_public_product_images.py).
            continue
        for method in operations:
            yield method.upper(), _PARAM.sub(str(uuid4()), path)


ROUTES = sorted(set(_protected_routes()))


def test_routes_are_registered() -> None:
    assert ROUTES


@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_route_requires_token(anonymous, method: str, path: str) -> None:
    response = anonymous.request(method, path, json={})
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), ROUTES)
def test_route_requires_permission(api_as, method: str, path: str) -> None:
    # Las dependencias de permiso se resuelven antes que el cuerpo y los parámetros.
    response = api_as("perm:other-service:all:all").request(method, path, json={})
    assert response.status_code == 403, (method, path, response.text)
