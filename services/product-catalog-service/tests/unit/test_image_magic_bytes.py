"""Primeros bytes del contenido frente al tipo declarado (spec 022, FR-022-92; T051, CP-29)."""

from __future__ import annotations

import pytest

from product_catalog_service.domain.image_content import SNIFF_BYTES, matches_declared_type

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 20


@pytest.mark.parametrize(("content", "mime"), [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")])
def test_valid_signatures(content: bytes, mime: str) -> None:
    assert matches_declared_type(content, mime)


@pytest.mark.parametrize(
    ("content", "mime"),
    [
        (PNG, "image/jpeg"),
        (JPEG, "image/png"),
        (b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 20, "image/webp"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/png"),
        (b"<html>", "image/jpeg"),
        (b"", "image/png"),
        (b"\x89PN", "image/png"),
        (PNG, "image/svg+xml"),
        (PNG, None),
    ],
)
def test_mismatches(content: bytes, mime) -> None:
    assert not matches_declared_type(content, mime)


def test_sniff_window_is_small() -> None:
    assert 12 <= SNIFF_BYTES <= 64
