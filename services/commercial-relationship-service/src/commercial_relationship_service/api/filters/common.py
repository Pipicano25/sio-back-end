"""Parámetros comunes de las colecciones (`contracts/rest-api.md`, reglas generales).

`search` admite hasta 100 caracteres y se recorta; sin `status` solo se
devuelven registros `ACTIVE` y `status=ALL` devuelve todos (R-13).
"""

from __future__ import annotations


def normalize_search(search: str | None) -> str | None:
    """Recorta la búsqueda; vacía equivale a no buscar."""
    if search is None:
        return None
    stripped = search.strip()
    return stripped or None
