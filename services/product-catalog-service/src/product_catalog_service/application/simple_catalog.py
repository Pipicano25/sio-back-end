"""Servicio genérico para catálogos codificados simples.

Lo usan unidades de medida, tipos de empaque, marcas y tipos de grupo: alta con
código normalizado e inmutable, modificación de campos permitidos, inactivación
y reactivación con versión esperada y auditoría desde la autenticación.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DuplicateCodeError,
    NotFoundError,
)
from product_catalog_service.application.normalization import (
    normalize_code,
    normalize_name,
    normalize_optional_text,
)
from product_catalog_service.application.pagination import PageResult, paginate
from product_catalog_service.infrastructure.locks import lock_row
from product_catalog_service.infrastructure.query_helpers import apply_common_filters

M = TypeVar("M")


class SimpleCatalogService(Generic[M]):
    """Operaciones comunes de un catálogo codificado."""

    model: type[M]
    label: str = "El registro"
    code_max_length: int = 50
    name_max_length: int = 120

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ lectura

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        code: str | None = None,
        search: str | None = None,
        extra_filters: Callable[[Any], Any] | None = None,
    ) -> PageResult:
        statement = apply_common_filters(
            select(self.model),
            self.model,
            status=status,
            code=code,
            search=search,
        )
        if extra_filters is not None:
            statement = extra_filters(statement)

        statement = statement.order_by(*self.default_order())
        return paginate(self.session, statement, page=page, page_size=page_size)

    def default_order(self) -> tuple:
        return (self.model.code,)

    def get(self, entity_id: UUID) -> M:
        entity = self.session.get(self.model, entity_id)
        if entity is None:
            raise NotFoundError(f"{self.label} {entity_id} no existe.")
        return entity

    # ---------------------------------------------------------------- escritura

    def create(self, *, code: str, name: str, actor: str, **fields: Any) -> M:
        normalized_code = normalize_code(code, max_length=self.code_max_length)
        self.before_create(normalized_code)

        if self._code_exists(normalized_code):
            raise DuplicateCodeError(f"Ya existe un registro con el código {normalized_code}.")

        entity = self.model(
            code=normalized_code,
            name=normalize_name(name, max_length=self.name_max_length),
            **self.prepare_fields(fields),
        )
        lifecycle.stamp_create(entity, actor)
        self.session.add(entity)
        self._commit_unique(normalized_code)
        return entity

    def update(self, entity_id: UUID, *, version: int, name: str, actor: str, **fields: Any) -> M:
        entity = lock_row(self.session, self.model, entity_id, label=self.label)
        lifecycle.check_version(entity, version)

        entity.name = normalize_name(name, max_length=self.name_max_length)
        for key, value in self.prepare_fields(fields).items():
            setattr(entity, key, value)
        self.before_update(entity)

        lifecycle.stamp_update(entity, actor)
        self.session.commit()
        return entity

    def deactivate(self, entity_id: UUID, *, version: int, actor: str) -> M:
        entity = lock_row(self.session, self.model, entity_id, label=self.label)
        self.before_deactivate(entity)
        lifecycle.deactivate(entity, version, actor)
        self.session.commit()
        return entity

    def reactivate(self, entity_id: UUID, *, version: int, actor: str) -> M:
        entity = lock_row(self.session, self.model, entity_id, label=self.label)
        self.before_reactivate(entity)
        lifecycle.reactivate(entity, version, actor)
        self.session.commit()
        return entity

    # ------------------------------------------------------------------ ganchos

    def prepare_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Normaliza los campos adicionales; por defecto `description` opcional."""
        prepared = dict(fields)
        if "description" in prepared:
            prepared["description"] = normalize_optional_text(prepared["description"])
        return prepared

    def before_create(self, code: str) -> None:
        return None

    def before_update(self, entity: M) -> None:
        return None

    def before_deactivate(self, entity: M) -> None:
        return None

    def before_reactivate(self, entity: M) -> None:
        return None

    # ---------------------------------------------------------------- utilidades

    def _code_exists(self, code: str) -> bool:
        return (
            self.session.execute(
                select(self.model.id).where(self.model.code == code)
            ).first()
            is not None
        )

    def _commit_unique(self, code: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if "uq_" in str(exc.orig):
                raise DuplicateCodeError(
                    f"Ya existe un registro con el código {code}."
                ) from None
            raise
