"""Tokens reales de Keycloak y clientes HTTP por identidad (research R-03).

- Usuarios de prueba: `password` grant con el cliente público `sio-web`.
- Identidades técnicas: `client_credentials` (solo para comprobar que son rechazadas: S-04, S-05).
- Renovación 60 s antes de vencer (lección de la 016).
- Cada petición lleva `traceparent` y queda en el diario (filtrado) con su duración.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import httpx

from .config import Secret, Settings
from .journal import Journal
from .run_context import RunContext

RENEW_BEFORE_SECONDS = 60.0
TEST_USERS = (
    "admin.test",
    "compras.test",
    "ventas.test",
    "supervisor.test",
    "consulta.test",
    "reportes.test",
    "inventario.test",
)
WEB_CLIENT = "sio-web"
DEFAULT_TIMEOUT = 30.0


class AuthError(RuntimeError):
    pass


def decode_claims(token: str) -> dict:
    """Claims del JWT sin verificar la firma (solo para leer `sub`, `exp` y permisos)."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))


def token_permissions(token: str, audience: str = "sio-api") -> set[str]:
    claims = decode_claims(token)
    roles = (claims.get("resource_access") or {}).get(audience, {}).get("roles", [])
    return set(roles)


@dataclass
class _Cached:
    token: str
    expires_at: float


class TokenProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.Client | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._settings = settings
        self._http = http or httpx.Client(timeout=DEFAULT_TIMEOUT)
        self._clock = clock
        self._cache: dict[str, _Cached] = {}
        self._lock = threading.Lock()

    def _request(self, form: Mapping[str, str], label: str) -> _Cached:
        response = self._http.post(self._settings.token_url, data=dict(form))
        if response.status_code != 200:
            # Nunca se incluye el cuerpo enviado (contiene la contraseña o el secreto).
            raise AuthError(f"Keycloak rechazó el token de {label}: HTTP {response.status_code}")
        body = response.json()
        return _Cached(body["access_token"], self._clock() + float(body.get("expires_in", 300)))

    def _get(self, key: str, form_factory: Callable[[], Mapping[str, str]], label: str) -> str:
        with self._lock:
            cached = self._cache.get(key)
            if cached and cached.expires_at - self._clock() > RENEW_BEFORE_SECONDS:
                return cached.token
            fresh = self._request(form_factory(), label)
            self._cache[key] = fresh
            return fresh.token

    def user_token(self, username: str) -> str:
        password = self._settings.secret("KEYCLOAK_TEST_USER_PASSWORD")
        if password is None:
            raise AuthError("Falta KEYCLOAK_TEST_USER_PASSWORD (entorno o infrastructure/.env)")

        def form() -> dict[str, str]:
            return {
                "grant_type": "password",
                "client_id": WEB_CLIENT,
                "username": username,
                "password": password.reveal(),
                "scope": "openid",
            }

        return self._get(f"user:{username}", form, username)

    def client_token(self, client_id: str, secret_variable: str) -> str:
        secret: Secret | None = self._settings.secret(secret_variable)
        if secret is None:
            raise AuthError(f"Falta {secret_variable} (entorno o infrastructure/.env)")

        def form() -> dict[str, str]:
            return {"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret.reveal()}

        return self._get(f"client:{client_id}", form, client_id)


@dataclass
class ApiResponse:
    status: int
    body: Any
    headers: Mapping[str, str]
    duration: float

    def json(self) -> Any:
        return self.body


class ApiClient:
    """Cliente HTTP de una identidad (usuario de prueba, identidad técnica, sin token o token inválido)."""

    def __init__(
        self,
        identity: str,
        settings: Settings,
        context: RunContext,
        journal: Journal,
        token: Callable[[], str | None],
        *,
        http: httpx.Client | None = None,
        stage: str = "",
    ) -> None:
        self.identity = identity
        self._settings = settings
        self._context = context
        self._journal = journal
        self._token = token
        self._http = http or httpx.Client(timeout=DEFAULT_TIMEOUT)
        self.stage = stage

    def request(
        self,
        method: str,
        service: str,
        path: str,
        *,
        step_id: str,
        json_body: Any = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        path_template: str | None = None,
        timeout: float | None = None,
        root: bool = False,
    ) -> ApiResponse:
        base = self._settings.service_url(service) if root else self._settings.api_base(service)
        url = base + path
        traceparent = self._context.traceparent()
        sent = {"traceparent": traceparent, "Accept": "application/json"}
        token = self._token()
        if token is not None:
            sent["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            sent["Idempotency-Key"] = idempotency_key
        if correlation_id:
            sent["X-Correlation-Id"] = correlation_id
        sent.update(headers or {})
        started = time.monotonic()
        error = None
        try:
            response = self._http.request(
                method,
                url,
                json=json_body,
                params=dict(params) if params else None,
                headers=sent,
                timeout=timeout or DEFAULT_TIMEOUT,
            )
            status = response.status_code
            try:
                body: Any = response.json() if response.content else None
            except ValueError:
                body = response.text
            response_headers = dict(response.headers)
        except httpx.HTTPError as exc:  # conexión rechazada, timeout…
            status, body, response_headers = 0, None, {}
            error = type(exc).__name__
        duration = time.monotonic() - started
        self._journal.record(
            {
                "step_id": step_id,
                "stage": self.stage,
                "identity": self.identity,
                "method": method,
                "service": service,
                "path": path_template or path,
                "resolved_path": path,
                "params": dict(params) if params else None,
                "status": status,
                "error": error,
                "traceparent": traceparent,
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
                "request_body": json_body,
                "response_body": body,
                "duration_seconds": round(duration, 3),
            }
        )
        return ApiResponse(status, body, response_headers, duration)

    def get(self, service: str, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", service, path, **kwargs)

    def post(self, service: str, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("POST", service, path, **kwargs)

    def patch(self, service: str, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PATCH", service, path, **kwargs)

    def put(self, service: str, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("PUT", service, path, **kwargs)


class Clients:
    """Fábrica de clientes por identidad, con el proveedor de tokens compartido."""

    def __init__(self, settings: Settings, context: RunContext, journal: Journal, stage: str = "") -> None:
        self.settings = settings
        self.context = context
        self.journal = journal
        self.tokens = TokenProvider(settings)
        self._http = httpx.Client(timeout=DEFAULT_TIMEOUT)
        self._clients: dict[str, ApiClient] = {}
        self.stage = stage

    def _make(self, identity: str, token: Callable[[], str | None]) -> ApiClient:
        client = self._clients.get(identity)
        if client is None:
            client = ApiClient(identity, self.settings, self.context, self.journal, token, http=self._http, stage=self.stage)
            self._clients[identity] = client
        client.stage = self.stage
        return client

    def user(self, username: str) -> ApiClient:
        return self._make(username, lambda: self.tokens.user_token(username))

    def service_account(self, client_id: str, secret_variable: str) -> ApiClient:
        return self._make(f"service-account-{client_id}", lambda: self.tokens.client_token(client_id, secret_variable))

    def anonymous(self) -> ApiClient:
        return self._make("sin-token", lambda: None)

    def invalid_token(self) -> ApiClient:
        # Token con forma JWT y firma inválida (no proviene de Keycloak).
        fake = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkbyJ9.ZmlybWEtaW52YWxpZGE"
        return self._make("token-invalido", lambda: fake)

    def set_stage(self, stage: str) -> None:
        self.stage = stage
        for client in self._clients.values():
            client.stage = stage
