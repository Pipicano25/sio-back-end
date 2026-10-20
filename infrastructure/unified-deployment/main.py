"""Despliegue unificado de SIO: los 12 microservicios en un solo proceso ASGI.

Modalidad adicional; no reemplaza los 12 despliegues independientes. Cada
microservicio se construye con su propia fábrica (`create_app`), sin cambios, y
se publica bajo un prefijo propio (`/geography`, `/sales`, …).

Por qué no `app.mount()`:

- Starlette conserva la ruta completa en `scope["path"]` dentro de un `Mount`, y
  `SIOAuthMiddleware` compara esa ruta con sus rutas públicas exactas: los health
  y `/docs` quedarían protegidos. Este despachador quita el prefijo de `path` y lo
  pasa en `root_path`, así cada aplicación ve las mismas rutas que en solitario y
  FastAPI sigue publicando `/docs` y `servers` con el prefijo correcto.
- Un `Mount` no ejecuta el `lifespan` de la aplicación montada; aquí se ejecuta el
  de cada una (Geography guarda su base de datos en `app.state` al arrancar).

Configuración: ver `registry.py` (entorno compartido más variables con prefijo).
Los workers corren en otro proceso (`workers.py`), administrado por `supervisor.py`;
aquí solo se expone su estado en `/health/workers`.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from collections.abc import Mapping
from contextlib import AsyncExitStack
from pathlib import Path

import anyio.to_thread
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sio_auth import install_cors
from starlette.types import ASGIApp, Receive, Scope, Send

from registry import SERVICES, Service, service_environment, state_dir, temporary_environment

__all__ = ["SERVICES", "Service", "app", "build_application", "service_environment", "temporary_environment"]

DEFAULT_THREAD_LIMIT = 100
# `workers.py` reescribe su estado cada pocos segundos; más viejo que esto = proceso caído o colgado.
WORKERS_STATUS_MAX_AGE_SECONDS = 60


def build_service_app(service: Service, environ: Mapping[str, str]) -> FastAPI:
    """Importa y construye el servicio con su entorno; después ya no vuelve a leerlo."""

    with temporary_environment(service_environment(service, environ)):
        module = importlib.import_module(service.module)
        app = getattr(module, "app", None)  # algunos construyen `app` al importar o al primer acceso
        if app is None:
            app = module.app_factory()  # Payment Reference
    return app


class UnifiedApplication:
    """Despacha por prefijo a cada microservicio y ejecuta el `lifespan` de todos."""

    def __init__(self, apps: Mapping[Service, FastAPI]) -> None:
        self.apps = dict(apps)
        self._root = build_root_app(self)
        self._routes = sorted(((s.path, a) for s, a in self.apps.items()), key=lambda item: -len(item[0]))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return

        path = scope["path"]
        for prefix, app in self._routes:
            if path == prefix or path.startswith(prefix + "/"):
                await app(_child_scope(scope, prefix), receive, send)
                return
        await self._root(scope, receive, send)

    async def _lifespan(self, receive: Receive, send: Send) -> None:
        await receive()  # lifespan.startup
        stack = AsyncExitStack()
        try:
            limiter = anyio.to_thread.current_default_thread_limiter()
            limiter.total_tokens = int(os.environ.get("SIO_UNIFIED_THREAD_LIMIT", DEFAULT_THREAD_LIMIT))
            for app in [*self.apps.values(), self._root]:
                await stack.enter_async_context(app.router.lifespan_context(app))
        except BaseException as exc:
            await stack.aclose()
            await send({"type": "lifespan.startup.failed", "message": repr(exc)})
            return
        await send({"type": "lifespan.startup.complete"})

        await receive()  # lifespan.shutdown
        try:
            await stack.aclose()
        except Exception as exc:
            await send({"type": "lifespan.shutdown.failed", "message": repr(exc)})
            return
        await send({"type": "lifespan.shutdown.complete"})


def _child_scope(scope: Scope, prefix: str) -> Scope:
    child = dict(scope)
    child["path"] = scope["path"][len(prefix):] or "/"
    child["root_path"] = scope.get("root_path", "") + prefix
    raw_path = scope.get("raw_path")
    if raw_path is not None:
        raw_prefix = prefix.encode()
        if raw_path.startswith(raw_prefix):
            child["raw_path"] = raw_path[len(raw_prefix):] or b"/"
        else:
            child.pop("raw_path")  # prefijo codificado de otra forma: Starlette usa `path`
    return child


def build_root_app(unified: UnifiedApplication) -> FastAPI:
    root = FastAPI(title="SIO — despliegue unificado", docs_url=None, redoc_url=None, openapi_url=None)

    @root.get("/")
    def index() -> dict:
        return {
            "deployment": "unified",
            "services": [
                {"name": s.prefix, "base": f"{s.path}{s.api_suffix}", "health": f"{s.path}/health/live", "docs": f"{s.path}/docs"}
                for s in unified.apps
            ],
            "workers": "/health/workers",
        }

    @root.get("/health/live")
    def live() -> dict:
        return {"status": "ok", "services": len(unified.apps)}

    @root.get("/health/ready")
    async def ready() -> JSONResponse:
        transport = httpx.ASGITransport(app=unified)
        statuses: dict[str, int] = {}
        async with httpx.AsyncClient(transport=transport, base_url="http://unified") as client:
            for service in unified.apps:
                response = await client.get(f"{service.path}/health/ready")
                statuses[service.prefix] = response.status_code
        healthy = all(code == 200 for code in statuses.values())
        return JSONResponse({"status": "ok" if healthy else "degraded", "services": statuses}, status_code=200 if healthy else 503)

    @root.get("/health/workers")
    def workers() -> JSONResponse:
        """Estado que publica `workers.py`; `503` si falta, está viejo o algún worker no está sano."""
        if os.environ.get("SIO_UNIFIED_WORKERS", "all").strip().lower() == "none":  # el supervisor no lo arranca
            return JSONResponse({"status": "disabled", "workers": {}}, status_code=200)
        path = Path(state_dir()) / "workers.json"
        try:
            status = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return JSONResponse({"status": "unavailable", "workers": {}}, status_code=503)
        if not status.get("enabled", True):
            return JSONResponse({"status": "disabled", "workers": {}}, status_code=200)
        stale = time.time() - float(status.get("written_at", 0)) > WORKERS_STATUS_MAX_AGE_SECONDS
        healthy = not stale and all(item.get("healthy") for item in status.get("workers", {}).values())
        body = {"status": "ok" if healthy else ("stale" if stale else "degraded"), **status}
        return JSONResponse(body, status_code=200 if healthy else 503)

    install_cors(root)
    return root


def build_application(environ: Mapping[str, str] | None = None) -> UnifiedApplication:
    source = dict(os.environ if environ is None else environ)
    return UnifiedApplication({service: build_service_app(service, source) for service in SERVICES})


app = build_application()
