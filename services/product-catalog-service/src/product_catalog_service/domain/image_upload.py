"""Validación de una imagen cargada directamente (spec 024, FR-024-11 a FR-024-14; research R4).

El tipo se deriva **del contenido**: nunca de la extensión ni del tipo declarado por el cliente. Orden:

1. presente y no vacío (`VALIDATION_ERROR`);
2. tamaño frente al límite (`FILE_TOO_LARGE`);
3. firma de los primeros bytes: JPEG, PNG o WebP (`UNSUPPORTED_MEDIA_TYPE`);
4. cabecera legible (`INVALID_IMAGE`);
5. píxeles (ancho × alto × cuadros) frente al límite, **antes** de decodificar (`IMAGE_DIMENSIONS_EXCEEDED`);
6. decodificación completa de todos los cuadros, coherente con la firma (`INVALID_IMAGE`).

La imagen se guarda tal cual (sin recodificar ni quitar EXIF).
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
import warnings
from dataclasses import dataclass

from PIL import Image, ImageFile

from product_catalog_service.application.exceptions import (
    FileTooLargeError,
    ImageDimensionsExceededError,
    InvalidImageError,
    UnsupportedMediaTypeError,
    ValidationError,
)

ImageFile.LOAD_TRUNCATED_IMAGES = False

MAX_FILE_NAME = 255
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_PIL_FORMAT = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    """Imagen aceptada: contenido, tipo real, SHA-256, clave y dimensiones."""

    content: bytes
    mime_type: str
    sha256: str
    width: int
    height: int

    @property
    def extension(self) -> str:
        return EXTENSIONS[self.mime_type]

    @property
    def key(self) -> str:
        """Clave del objeto: `assets/<sha256>.<ext>` (FR-024-13); el nombre del usuario nunca forma parte."""
        return f"assets/{self.sha256}.{self.extension}"

    @property
    def size(self) -> int:
        return len(self.content)


def sniff_mime(head: bytes) -> str | None:
    """Tipo real por la firma de los primeros bytes, o `None` si no es JPEG, PNG ni WebP."""
    if head.startswith(_PNG):
        return "image/png"
    if head.startswith(_JPEG):
        return "image/jpeg"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(content: bytes | None, *, max_bytes: int, max_pixels: int) -> ValidatedImage:
    """Valida el archivo en el orden de FR-024-11 y devuelve la imagen aceptada."""
    if not content:
        raise ValidationError("Debe enviar un archivo de imagen no vacío en el campo file.", field="file")
    if len(content) > max_bytes:
        raise FileTooLargeError(
            f"El archivo supera el tamaño máximo permitido ({max_bytes} bytes).", extra={"max_bytes": max_bytes}
        )
    mime = sniff_mime(content[:16])
    if mime is None:
        raise UnsupportedMediaTypeError("Solo se admiten imágenes JPEG, PNG o WebP (según su contenido real).")

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            image = Image.open(io.BytesIO(content))
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise _too_many_pixels(max_pixels) from exc
        except Exception as exc:  # cualquier fallo de Pillow al leer la cabecera
            raise InvalidImageError("El archivo no es una imagen íntegra.") from exc

        with image:
            if image.format != _PIL_FORMAT[mime]:
                raise InvalidImageError("El contenido no corresponde a una imagen íntegra de su tipo.")
            width, height = image.size
            frames = max(int(getattr(image, "n_frames", 1) or 1), 1)
            if width <= 0 or height <= 0:
                raise InvalidImageError("La imagen no tiene dimensiones válidas.")
            if width * height * frames > max_pixels:
                raise _too_many_pixels(max_pixels)
            try:
                for frame in range(frames):
                    image.seek(frame)
                    image.load()
            except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
                raise _too_many_pixels(max_pixels) from exc
            except Exception as exc:  # truncada, corrupta o con datos inválidos
                raise InvalidImageError("El archivo no es una imagen íntegra.") from exc

    return ValidatedImage(
        content=content,
        mime_type=mime,
        sha256=hashlib.sha256(content).hexdigest(),
        width=width,
        height=height,
    )


def _too_many_pixels(max_pixels: int) -> ImageDimensionsExceededError:
    return ImageDimensionsExceededError(
        f"La imagen supera el máximo de {max_pixels} píxeles.", extra={"max_pixels": max_pixels}
    )


def sanitize_file_name(value: str | None, extension: str) -> str:
    """Nombre original saneado (FR-024-14): sin rutas ni caracteres de control, ≤ 255; `image.<ext>` si queda vacío."""
    name = unicodedata.normalize("NFC", value or "")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = _CONTROL.sub("", name).strip().strip(".").strip()
    if not name:
        return f"image.{extension}"
    if len(name) > MAX_FILE_NAME:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            name = f"{stem[: MAX_FILE_NAME - len(ext) - 1]}.{ext}"
        else:
            name = name[:MAX_FILE_NAME]
    return name
