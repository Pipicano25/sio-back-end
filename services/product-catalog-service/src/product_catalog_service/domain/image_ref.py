"""Imágenes por URL directa (spec 022, FR-022-45, FR-022-46, FR-022-91, FR-022-97). Funciones puras.

- `eligible_image_sha`: un activo es apto para URL si es la imagen principal `ACTIVE`, su contenido
  está en el almacenamiento de SIO (`s3://<bucket>/<clave>`), su tipo es JPEG, PNG o WebP y su clave
  deriva del SHA-256 del contenido. Devuelve ese SHA-256 o `None`.
- `sign_ref` / `verify_ref`: referencia opaca de **un** activo y **una** versión de su contenido:
  `base64url(asset_id ‖ sha256[:8]) . base64url(HMAC-SHA256(secreto, asset_id ‖ sha256[:8])[:16])`.
  128 bits de firma; la verificación es en tiempo constante y acepta el secreto anterior durante una
  rotación. No hay forma de derivar la referencia de otro activo.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MIN_SECRET_BYTES = 32
MAX_REF_LENGTH = 128
SHA_PREFIX_BYTES = 8
SIGNATURE_BYTES = 16

_SHA256_IN_KEY = re.compile(r"(?<![0-9a-f])([0-9a-f]{64})(?![0-9a-f])")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PAYLOAD_BYTES = 16 + SHA_PREFIX_BYTES


def sha_from_key(key: str) -> str | None:
    """SHA-256 incluido en la clave del objeto (`assets/<sha256>...`), o `None`."""
    match = _SHA256_IN_KEY.search(key or "")
    return match.group(1) if match else None


def eligible_image_sha(asset: Any, bucket: str, *, require_primary: bool = True) -> str | None:
    """SHA-256 del contenido si el activo es una imagen apta para URL (FR-022-46).

    `has_image` exige la imagen principal; la ruta pública (`require_primary=False`) sigue sirviendo una URL ya
    emitida mientras su activo esté `ACTIVE` (historia 2, escenario 3).
    """
    if asset.asset_type != "IMAGE" or asset.status != "ACTIVE" or (require_primary and not asset.is_primary):
        return None
    if asset.mime_type not in ALLOWED_IMAGE_TYPES:
        return None
    parsed = urlparse(asset.storage_uri or "")
    key = parsed.path.lstrip("/")
    if parsed.scheme != "s3" or parsed.netloc != bucket or not key:
        return None
    return sha_from_key(key)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(secret: str, payload: bytes) -> bytes:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()[:SIGNATURE_BYTES]


def sign_ref(asset_id: UUID, sha256_hex: str, secret: str) -> str:
    """Referencia firmada de un activo y una versión de su contenido."""
    if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
        raise ValueError(f"El secreto debe tener al menos {MIN_SECRET_BYTES} bytes.")
    if not _SHA256.match(sha256_hex or ""):
        raise ValueError("El SHA-256 del contenido no es válido.")
    payload = asset_id.bytes + bytes.fromhex(sha256_hex)[:SHA_PREFIX_BYTES]
    return f"{_b64(payload)}.{_b64(_signature(secret, payload))}"


def verify_ref(ref: Any, secrets: Sequence[str]) -> tuple[UUID, str] | None:
    """`(asset_id, prefijo hexadecimal del SHA-256)` si la referencia es válida; `None` en cualquier otro caso."""
    if not isinstance(ref, str) or not ref or len(ref) > MAX_REF_LENGTH or ref.count(".") != 1:
        return None
    encoded_payload, encoded_signature = ref.split(".")
    try:
        payload = _unb64(encoded_payload)
        signature = _unb64(encoded_signature)
    except (binascii.Error, ValueError):
        return None
    if len(payload) != _PAYLOAD_BYTES or len(signature) != SIGNATURE_BYTES:
        return None
    # Forma canónica: rechaza codificaciones alternativas del mismo contenido.
    if _b64(payload) != encoded_payload or _b64(signature) != encoded_signature:
        return None
    valid = False
    for secret in secrets:
        if secret and hmac.compare_digest(_signature(secret, payload), signature):
            valid = True
    if not valid:
        return None
    return UUID(bytes=payload[:16]), payload[16:].hex()
