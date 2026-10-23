"""Imágenes reales generadas con Pillow para las pruebas de la spec 024 (datos ficticios)."""

from __future__ import annotations

import io

from PIL import Image


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (8, 6), color=(200, 30, 30), **save) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt, **save)
    return buffer.getvalue()


def png(color=(200, 30, 30), size=(8, 6)) -> bytes:
    return image_bytes("PNG", size, color)


def jpeg(color=(30, 200, 30), size=(8, 6)) -> bytes:
    return image_bytes("JPEG", size, color, quality=90)


def webp(color=(30, 30, 200), size=(8, 6)) -> bytes:
    return image_bytes("WEBP", size, color)


def animated_webp(frames: int = 3, size=(8, 6)) -> bytes:
    buffer = io.BytesIO()
    images = [Image.new("RGB", size, (index * 60, 10, 10)) for index in range(frames)]
    images[0].save(buffer, format="WEBP", save_all=True, append_images=images[1:], duration=100)
    return buffer.getvalue()


def gif(size=(8, 6)) -> bytes:
    return image_bytes("GIF", size, (1, 2, 3))
