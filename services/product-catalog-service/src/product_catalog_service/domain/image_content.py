"""Verificación de los primeros bytes de una imagen frente a su tipo declarado (spec 022, FR-022-92).

Evita entregar como imagen un contenido de otro tipo (HTML, SVG con scripts…) aunque su activo diga `image/png`.
"""

from __future__ import annotations

SNIFF_BYTES = 16
"""Bytes iniciales necesarios para reconocer JPEG, PNG y WebP."""

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"


def matches_declared_type(head: bytes, mime_type: str | None) -> bool:
    """`True` si los primeros bytes corresponden al tipo declarado (solo JPEG, PNG y WebP)."""
    if mime_type == "image/png":
        return head.startswith(_PNG)
    if mime_type == "image/jpeg":
        return head.startswith(_JPEG)
    if mime_type == "image/webp":
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return False
