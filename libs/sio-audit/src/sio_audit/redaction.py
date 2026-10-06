"""Política única de redacción de valores sensibles (FR-017, FR-017a; R-07).

La misma función se aplica en el emisor antes de escribir en su outbox y otra
vez en Audit al recibir el evento (defensa en profundidad). Nunca rechaza un
evento: reemplaza el valor de cada clave sensible por `"***"` y devuelve las
rutas ocultadas, ordenadas y sin duplicados.

Una clave es sensible si su nombre, en minúsculas y sin `-` ni `_`, es
exactamente uno de `SENSITIVE_KEYS`. La coincidencia es exacta (no por
subcadena) para no ocultar por error campos como `token_count` o
`password_policy_id`. Ampliar la lista es un cambio de versión de la librería y
del contrato del evento.

Este módulo nunca registra valores en logs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

POLICY_VERSION = 1
"""Versión de la política publicada en el contrato del evento."""

REDACTED_VALUE = "***"

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "clientsecret",
        "token",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "authorization",
        "apikey",
        "credential",
        "credentials",
        "privatekey",
    }
)

MAX_DEPTH = 10
"""Niveles de anidamiento que se recorren (igual al límite del contrato)."""


@dataclass(frozen=True, slots=True)
class RedactionResult:
    """Valores ya redactados y rutas ocultadas (unidas con las recibidas)."""

    previous_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    paths: tuple[str, ...]


def normalize_key(key: str) -> str:
    """Nombre de clave normalizado para comparar con la política."""
    return key.lower().replace("-", "").replace("_", "")


def is_sensitive_key(key: Any) -> bool:
    """Indica si una clave pertenece a la política de redacción."""
    return isinstance(key, str) and normalize_key(key) in SENSITIVE_KEYS


def _redact(value: Any, path: str, found: list[str], depth: int) -> Any:
    if depth > MAX_DEPTH:
        # Más profundo que el contrato: la validación del evento lo rechaza por
        # profundidad; aquí no se recorre para no ocultar nada a medias.
        return value

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}

        for key, item in value.items():
            child = f"{path}.{key}"

            if is_sensitive_key(key):
                found.append(child)
                result[key] = REDACTED_VALUE
            else:
                result[key] = _redact(item, child, found, depth + 1)

        return result

    if isinstance(value, list):
        return [_redact(item, f"{path}[{index}]", found, depth + 1) for index, item in enumerate(value)]

    return value


def redact(
    previous_values: Mapping[str, Any] | None,
    new_values: Mapping[str, Any] | None,
    existing_paths: Iterable[str] = (),
) -> RedactionResult:
    """Oculta los valores sensibles de `previous_values` y `new_values`.

    No modifica las estructuras recibidas. Las rutas usan `.` para objetos y
    `[i]` para listas, con el campo raíz como prefijo, p. ej.
    `new_values.contacts[0].api_key`.

    Args:
        previous_values: Valores anteriores del evento, o `None`.
        new_values: Valores nuevos del evento, o `None`.
        existing_paths: Rutas que ya ocultó el emisor.

    Returns:
        Valores redactados y rutas ocultadas, ordenadas y sin duplicados.
    """
    found: list[str] = [path for path in existing_paths if isinstance(path, str)]

    previous = (
        None if previous_values is None else _redact(previous_values, "previous_values", found, 1)
    )
    new = None if new_values is None else _redact(new_values, "new_values", found, 1)

    return RedactionResult(
        previous_values=previous,
        new_values=new,
        paths=tuple(sorted(set(found))),
    )
