"""Configuración propia de Payment Reference Service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración propia del microservicio.

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
    """

    docs_enabled: bool
    database_url: str


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Returns:
        Configuración obtenida desde el entorno.

    Raises:
        RuntimeError: Si falta una configuración obligatoria o si una
            variable booleana contiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool(
            name="SIO_DOCS_ENABLED",
            default=False,
        ),
        database_url=_required_text("DATABASE_URL"),
    )


def _required_text(name: str) -> str:
    """Obtiene una variable de entorno de texto obligatoria.

    Args:
        name: Nombre de la variable de entorno.

    Returns:
        Valor no vacío de la variable.

    Raises:
        RuntimeError: Si la variable no existe o está vacía.
    """
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable de entorno {name} es obligatoria y no puede estar vacía."
        )

    return value.strip()


def _read_bool(name: str, default: bool) -> bool:
    """Obtiene una variable de entorno booleana.

    Args:
        name: Nombre de la variable de entorno.
        default: Valor utilizado cuando la variable no está definida.

    Returns:
        Valor booleano interpretado.

    Raises:
        RuntimeError: Si el valor no representa un booleano válido.
    """
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if normalized_value in {"true", "1", "yes", "on"}:
        return True

    if normalized_value in {"false", "0", "no", "off"}:
        return False

    raise RuntimeError(
        f"La variable de entorno {name} debe contener un valor booleano válido."
    )
