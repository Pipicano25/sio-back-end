"""Validación del archivo cargado (spec 024, casos 2 a 7; FR-024-11 a FR-024-14)."""

from __future__ import annotations

import hashlib

import pytest

from product_catalog_service.application.exceptions import (
    FileTooLargeError,
    ImageDimensionsExceededError,
    InvalidImageError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from product_catalog_service.domain.image_upload import sanitize_file_name, sniff_mime, validate_image
from tests import images

LIMITS = {"max_bytes": 5_242_880, "max_pixels": 40_000_000}


@pytest.mark.parametrize(
    ("content", "mime", "extension"),
    [(images.jpeg(), "image/jpeg", "jpg"), (images.png(), "image/png", "png"), (images.webp(), "image/webp", "webp")],
)
def test_accepts_jpeg_png_and_webp_with_real_type_and_sha_key(content, mime, extension) -> None:
    image = validate_image(content, **LIMITS)
    sha = hashlib.sha256(content).hexdigest()
    assert (image.mime_type, image.extension, image.sha256) == (mime, extension, sha)
    assert image.key == f"assets/{sha}.{extension}"
    assert (image.width, image.height) == (8, 6)


def test_animated_webp_is_accepted_when_it_decodes_within_limits() -> None:
    assert validate_image(images.animated_webp(), **LIMITS).mime_type == "image/webp"


@pytest.mark.parametrize(
    "content",
    [
        b"<!doctype html><html><body>no</body></html>",
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj",
        images.gif(),
        b"BM" + b"\x00" * 64,
    ],
    ids=["html", "svg", "pdf", "gif", "bmp"],
)
def test_rejects_other_formats_by_content(content) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        validate_image(content, **LIMITS)


def test_declared_type_or_extension_do_not_matter() -> None:
    # La validación solo recibe bytes: un PNG renombrado .jpg se guarda como PNG.
    assert validate_image(images.png(), **LIMITS).mime_type == "image/png"


@pytest.mark.parametrize("content", [None, b""])
def test_rejects_missing_or_empty_file(content) -> None:
    with pytest.raises(ValidationError):
        validate_image(content, **LIMITS)


def test_rejects_truncated_image() -> None:
    content = images.jpeg(size=(64, 64))
    with pytest.raises(InvalidImageError):
        validate_image(content[: len(content) // 2], **LIMITS)


def test_rejects_corrupt_image_with_valid_signature() -> None:
    with pytest.raises(InvalidImageError):
        validate_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, **LIMITS)


def test_size_limit_boundary_exact_is_accepted_and_one_more_is_rejected() -> None:
    content = images.png()
    assert validate_image(content, max_bytes=len(content), max_pixels=100).size == len(content)
    with pytest.raises(FileTooLargeError):
        validate_image(content, max_bytes=len(content) - 1, max_pixels=100)


def test_size_is_checked_before_content_type() -> None:
    with pytest.raises(FileTooLargeError):
        validate_image(b"<html>" * 100, max_bytes=10, max_pixels=100)


def test_pixel_limit_boundary() -> None:
    content = images.png(size=(10, 10))
    assert validate_image(content, max_bytes=10_000, max_pixels=100).width == 10
    with pytest.raises(ImageDimensionsExceededError):
        validate_image(content, max_bytes=10_000, max_pixels=99)


def test_animated_frames_count_towards_pixel_limit() -> None:
    with pytest.raises(ImageDimensionsExceededError):
        validate_image(images.animated_webp(frames=3, size=(10, 10)), max_bytes=100_000, max_pixels=250)


def test_sniff_mime() -> None:
    assert sniff_mime(images.png()[:16]) == "image/png"
    assert sniff_mime(b"GIF89a") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("frente.png", "frente.png"),
        ("C:\\fotos\\botella 600.jpg", "botella 600.jpg"),
        ("../../etc/passwd", "passwd"),
        ("ma\x00la\x1f.png", "mala.png"),
        ("", "image.png"),
        (None, "image.png"),
        ("   ", "image.png"),
        ("/", "image.png"),
    ],
)
def test_sanitize_file_name(raw, expected) -> None:
    assert sanitize_file_name(raw, "png") == expected


def test_sanitize_file_name_limits_to_255_keeping_extension() -> None:
    name = sanitize_file_name("a" * 400 + ".webp", "webp")
    assert len(name) == 255 and name.endswith(".webp")
