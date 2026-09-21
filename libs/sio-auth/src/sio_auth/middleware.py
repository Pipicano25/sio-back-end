"""Middleware ASGI de autenticación con comportamiento fail-closed."""

from __future__ import annotations

from collections.abc import Collection

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .errors import AuthenticationError
from .tokens import AccessTokenDecoder


class SIOAuthMiddleware:
    """Autentica todas las rutas HTTP excepto una lista pública explícita de coincidencia exacta."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        decoder: AccessTokenDecoder,
        public_paths: Collection[str] = (),
    ) -> None:
        self._app = app
        self._decoder = decoder
        self._public_paths = frozenset(_normalize_public_path(p) for p in public_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._public_paths:
            await self._app(scope, receive, send)
            return

        authorization = _header(scope, b"authorization")
        token = _extract_bearer_token(authorization)
        if token is None:
            await _unauthorized(send, "Se requiere un token de acceso Bearer")
            return

        try:
            claims = await run_in_threadpool(self._decoder.decode, token)
        except AuthenticationError as exc:
            await _unauthorized(send, exc.message)
            return

        state = scope.setdefault("state", {})
        state["sio_claims"] = claims
        await self._app(scope, receive, send)


def _normalize_public_path(path: str) -> str:
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("las rutas públicas deben ser rutas absolutas que comiencen con '/'")
    return path


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            try:
                return value.decode("latin-1")
            except UnicodeDecodeError:
                return None
    return None


def _extract_bearer_token(value: str | None) -> str | None:
    if value is None:
        return None
    parts = value.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        return None
    return parts[1]


async def _unauthorized(send: Send, detail: str) -> None:
    response = JSONResponse(
        status_code=401,
        content={"detail": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )
    await response({"type": "http"}, _empty_receive, send)


async def _empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}
