"""Forma canónica de una solicitud y su huella determinista `request_hash` (R-03).

- Claves de objetos ordenadas; JSON compacto en UTF-8.
- UUID en minúsculas (también los recibidos como texto con forma de UUID).
- Decimales normalizados sin ceros a la derecha (`domain.quantities`).
- Textos recortados; ausente = `null`.
- Las listas conservan su orden (el orden de las líneas es parte de la solicitud).

`request_hash` = SHA-256 de `canonical_json + "\\n" + client_id + "\\n" + operation_type`:
la misma solicitud del mismo cliente produce siempre la misma huella; cualquier
diferencia de contenido, cliente o tipo produce otra.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from inventory_service.domain.quantities import normalize_decimal


def _as_uuid_text(value: str) -> str | None:
    try:
        parsed = UUID(value)
    except ValueError:
        return None

    return str(parsed) if len(value) == 36 else None


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, bool | int):
        return value

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return normalize_decimal(value)

    if isinstance(value, str):
        stripped = value.strip()
        return _as_uuid_text(stripped) or stripped

    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in value.items()}

    if isinstance(value, Sequence):
        return [_canonical(item) for item in value]

    raise TypeError(f"Tipo no admitido en la forma canónica: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """JSON canónico (claves ordenadas, sin espacios)."""
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_hash(payload: Mapping[str, Any], client_id: str, operation_type: str) -> str:
    """Huella determinista de una solicitud de operación o de reverso."""
    material = f"{canonical_json(payload)}\n{client_id}\n{operation_type}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
