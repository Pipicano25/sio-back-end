"""Modelos inmutables de permisos utilizados por sio-auth."""

from __future__ import annotations

from dataclasses import dataclass
import re

_PERMISSION_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _validate_segment(value: str, *, name: str, allow_all: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} debe ser una cadena de texto")

    value = value.strip()
    if not value:
        raise ValueError(f"{name} no puede estar vacío")

    if value == "all":
        if allow_all:
            return value
        raise ValueError(f"{name} no puede ser 'all' en un permiso concreto")

    if not _PERMISSION_SEGMENT.fullmatch(value):
        raise ValueError(
            f"{name} solo puede contener letras minúsculas, números, '_' o '-'"
        )

    return value


@dataclass(frozen=True, slots=True)
class SioPermission:
    """Permiso concreto requerido por una operación de la API.

    sio-auth no mantiene catálogos de servicios, recursos, acciones, grupos,
    roles ni permisos. Los tres valores los proporciona el microservicio al
    declarar el requisito de autorización.
    """

    service: str
    resource: str
    action: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "service",
            _validate_segment(self.service, name="service"),
        )
        object.__setattr__(
            self,
            "resource",
            _validate_segment(self.resource, name="resource"),
        )
        object.__setattr__(
            self,
            "action",
            _validate_segment(self.action, name="action"),
        )

    def __str__(self) -> str:
        return f"perm:{self.service}:{self.resource}:{self.action}"


@dataclass(frozen=True, slots=True)
class SioGrant:
    """Permiso concedido obtenido dinámicamente desde un client role de Keycloak.

    Cada segmento puede ser ``all``. Keycloak transporta el texto del rol y
    sio-auth únicamente interpreta ``all`` al comparar ese grant con el permiso
    concreto exigido por un endpoint.
    """

    service: str
    resource: str
    action: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "service",
            _validate_segment(self.service, name="service", allow_all=True),
        )
        object.__setattr__(
            self,
            "resource",
            _validate_segment(self.resource, name="resource", allow_all=True),
        )
        object.__setattr__(
            self,
            "action",
            _validate_segment(self.action, name="action", allow_all=True),
        )

    def allows(self, required: SioPermission) -> bool:
        return (
            self.service in {"all", required.service}
            and self.resource in {"all", required.resource}
            and self.action in {"all", required.action}
        )

    def __str__(self) -> str:
        return f"perm:{self.service}:{self.resource}:{self.action}"
