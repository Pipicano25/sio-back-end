"""CORS abierto para los microservicios de SIO (0.5.0).

Las API se consumen desde cualquier frontend, en cualquier dominio. CORS no es un
control de acceso: la seguridad sigue en el Bearer Access Token, sus permisos y la
membresía operativa. Por eso:

- se admite cualquier origen (`Access-Control-Allow-Origin: *`);
- nunca se admiten credenciales del navegador (SIO no usa cookies), de modo que no
  se envía `Access-Control-Allow-Credentials: true`;
- el preflight `OPTIONS` se responde antes de `SIOAuthMiddleware`, sin token.

`install_cors` envuelve la pila completa de la aplicación, incluido el
`ServerErrorMiddleware` de Starlette. Así también los `401` de sio-auth y los `500`
no controlados llevan las cabeceras CORS, algo que `app.add_middleware` no garantiza.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

CORS_ALLOW_ORIGINS = ("*",)
CORS_ALLOW_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOW_HEADERS = ("*",)
CORS_EXPOSE_HEADERS = ("X-Trace-Id", "Content-Disposition")
CORS_MAX_AGE_SECONDS = 600

_INSTALLED_ATTRIBUTE = "_sio_cors_installed"


def install_cors(app: Starlette) -> None:
    """Hace de CORS la capa más externa de `app`; llamarla dos veces no tiene efecto."""

    if getattr(app, _INSTALLED_ATTRIBUTE, False):
        return
    if app.middleware_stack is not None:
        raise RuntimeError("install_cors debe llamarse antes de que la aplicación arranque")

    build_stack = app.build_middleware_stack

    def build_stack_with_cors() -> ASGIApp:
        return CORSMiddleware(
            build_stack(),
            allow_origins=list(CORS_ALLOW_ORIGINS),
            allow_credentials=False,
            allow_methods=list(CORS_ALLOW_METHODS),
            allow_headers=list(CORS_ALLOW_HEADERS),
            expose_headers=list(CORS_EXPOSE_HEADERS),
            max_age=CORS_MAX_AGE_SECONDS,
        )

    app.build_middleware_stack = build_stack_with_cors  # type: ignore[method-assign]
    setattr(app, _INSTALLED_ATTRIBUTE, True)
