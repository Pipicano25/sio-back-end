"""Cursor de paginación firmado y sin estado (FR-022-145 a FR-022-151; `contracts/cursor.md`; research R-08).

Formato `v1.<contenido>.<firma>`: contenido = base64url de un JSON canónico; firma = base64url de
`HMAC-SHA256(secreto, "v1." + contenido)`, verificada en tiempo constante con el secreto actual o el anterior
(rotación). Vence a los `ttl` segundos, con 30 s de tolerancia de reloj. No contiene tokens, credenciales,
permisos, ids de usuario ni listas de ids: solo la posición *keyset* que entregó el conductor.

`evaluate` aplica la tabla de FR-022-149 **después** de autenticar y autorizar al usuario:

| Paso | Situación | Resultado |
|---|---|---|
| 1 | Sin cursor | `FIRST` |
| 2–4 | Malformado, versión desconocida, demasiado largo, firma o contenido inválidos | `INVALID` |
| 5 | Otra empresa | `INVALID` |
| 6 | Otro endpoint | `INVALID` |
| 7 | Vencido | `RESET` `CURSOR_EXPIRED` |
| 8 | Otros filtros | `RESET` `FILTERS_CHANGED` |
| 9 | Otro orden | `RESET` `SORT_CHANGED` |
| 10 | Otro `page_size` | `RESET` `PAGE_SIZE_CHANGED` |
| 11 | Otra ruta con todo lo demás igual | `INVALID` (imposible con un plan determinista; se registra como error) |
| 12 | Todo igual | `CONTINUE` |
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from product_inventory_query_service.application.exceptions import InvalidCursorError
from product_inventory_query_service.domain.query_spec import MAX_CURSOR_LENGTH

logger = logging.getLogger("product_inventory_query_service")

VERSION = 1
PREFIX = "v1"
CLOCK_SKEW_SECONDS = 30
KINDS = ("PAGE", "SCAN")
FIELDS = {"v", "ep", "cid", "fh", "sort", "ps", "route", "k", "pos", "iat", "exp"}


class Decision(str, Enum):
    FIRST = "FIRST"
    CONTINUE = "CONTINUE"
    RESET = "RESET"


class ResetReason(str, Enum):
    CURSOR_EXPIRED = "CURSOR_EXPIRED"
    FILTERS_CHANGED = "FILTERS_CHANGED"
    SORT_CHANGED = "SORT_CHANGED"
    PAGE_SIZE_CHANGED = "PAGE_SIZE_CHANGED"


@dataclass(frozen=True, slots=True)
class CursorPayload:
    ep: str
    cid: str
    fh: str
    sort: str
    ps: int
    route: str
    k: str
    pos: dict[str, Any]
    iat: int
    exp: int
    v: int = VERSION

    def to_json(self) -> dict:
        return {"v": self.v, "ep": self.ep, "cid": self.cid, "fh": self.fh, "sort": self.sort, "ps": self.ps,
                "route": self.route, "k": self.k, "pos": self.pos, "iat": self.iat, "exp": self.exp}


@dataclass(frozen=True, slots=True)
class CursorResult:
    decision: Decision
    reason: ResetReason | None = None
    payload: CursorPayload | None = None


@dataclass(frozen=True, slots=True)
class Expected:
    """Lo que la solicitud actual espera de un cursor válido."""

    endpoint: str
    company_id: str
    fingerprint: str
    sort: str
    page_size: int
    route: str


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    if not text or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in text):
        raise ValueError("base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class CursorCodec:
    def __init__(self, secret: str, previous: str | None = None, *, ttl_seconds: int = 900,
                 clock: Callable[[], float] = time.time) -> None:
        self._secrets: Sequence[bytes] = [s.encode("utf-8") for s in (secret, previous) if s]
        self._ttl = ttl_seconds
        self._clock = clock

    def _sign(self, secret: bytes, message: bytes) -> bytes:
        return hmac.new(secret, message, hashlib.sha256).digest()

    def issue(self, expected: Expected, *, kind: str, position: dict[str, Any]) -> str:
        if kind not in KINDS:
            raise ValueError(kind)
        now = int(self._clock())
        payload = CursorPayload(ep=expected.endpoint, cid=expected.company_id, fh=expected.fingerprint,
                                sort=expected.sort, ps=expected.page_size, route=expected.route, k=kind,
                                pos=position, iat=now, exp=now + self._ttl)
        content = _b64(json.dumps(payload.to_json(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        message = f"{PREFIX}.{content}".encode("ascii")
        return f"{PREFIX}.{content}.{_b64(self._sign(self._secrets[0], message))}"

    def decode(self, text: str) -> CursorPayload:
        """Formato, firma y contenido; cualquier falla es `InvalidCursorError` (pasos 2 a 4)."""
        if len(text) > MAX_CURSOR_LENGTH:
            raise InvalidCursorError("longitud")
        parts = text.split(".")
        if len(parts) != 3 or parts[0] != PREFIX:
            raise InvalidCursorError("formato")
        try:
            signature = _unb64(parts[2])
            content = _unb64(parts[1])
        except (ValueError, binascii.Error):
            raise InvalidCursorError("base64") from None
        message = f"{PREFIX}.{parts[1]}".encode("ascii")
        valid = False
        for secret in self._secrets:
            if hmac.compare_digest(self._sign(secret, message), signature):
                valid = True
        if not valid:
            raise InvalidCursorError("firma")
        try:
            data = json.loads(content)
            if not isinstance(data, dict) or set(data) != FIELDS or data["v"] != VERSION or data["k"] not in KINDS:
                raise ValueError("campos")
            if not isinstance(data["pos"], dict) or not isinstance(data["ps"], int):
                raise ValueError("tipos")
            return CursorPayload(**data)
        except (ValueError, TypeError, KeyError):
            raise InvalidCursorError("contenido") from None

    def evaluate(self, text: str | None, expected: Expected) -> CursorResult:
        if text is None:
            return CursorResult(Decision.FIRST)
        payload = self.decode(text)
        if payload.cid != expected.company_id:
            raise InvalidCursorError("empresa")
        if payload.ep != expected.endpoint:
            raise InvalidCursorError("endpoint")
        if self._clock() > payload.exp + CLOCK_SKEW_SECONDS:
            return CursorResult(Decision.RESET, ResetReason.CURSOR_EXPIRED)
        if payload.fh != expected.fingerprint:
            return CursorResult(Decision.RESET, ResetReason.FILTERS_CHANGED)
        if payload.sort != expected.sort:
            return CursorResult(Decision.RESET, ResetReason.SORT_CHANGED)
        if payload.ps != expected.page_size:
            return CursorResult(Decision.RESET, ResetReason.PAGE_SIZE_CHANGED)
        if payload.route != expected.route:
            logger.error("Cursor con otra ruta y la misma huella: el plan debería ser determinista")
            raise InvalidCursorError("ruta")
        return CursorResult(Decision.CONTINUE, payload=payload)
