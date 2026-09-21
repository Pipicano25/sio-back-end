import os
from dataclasses import dataclass


_TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "on",
}

_FALSE_VALUES = {
    "0",
    "false",
    "no",
    "off",
}


@dataclass(frozen=True)
class Settings:
    docs_enabled: bool
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            docs_enabled=_get_bool_env(
                "SIO_DOCS_ENABLED",
                default=False,
            ),
            database_url=_get_required_env(
                "DATABASE_URL",
            ),
        )


def _get_required_env(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable de entorno {name} es obligatoria."
        )

    return value.strip()


def _get_bool_env(
    name: str,
    *,
    default: bool,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
        return False

    raise RuntimeError(
        f"La variable de entorno {name} debe contener "
        "un valor booleano válido."
    )