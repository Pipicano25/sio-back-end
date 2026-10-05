"""Utilidades de persistencia compartidas por los repositorios SQLAlchemy.

Traducen errores de la base a excepciones de aplicación sin filtrar detalles
del motor (Principio XII) y aplican el control de versión esperado
(Principio VII; R-08, R-14).
"""

from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from commercial_relationship_service.application.exceptions import (
    CommercialRelationshipError,
    NotFoundError,
    VersionConflictError,
)

ModelT = TypeVar("ModelT")


def load_for_update(
    session: Session,
    model_class: type[ModelT],
    entity_id: UUID,
    *,
    expected_version: int,
) -> ModelT:
    """Carga la fila con `SELECT ... FOR UPDATE` y comprueba la versión esperada.

    Raises:
        NotFoundError: Si la fila no existe.
        VersionConflictError: Si la versión no coincide.
    """
    try:
        model = session.get(
            model_class,
            entity_id,
            with_for_update=True,
            populate_existing=True,
        )
    except StaleDataError:
        # La fila ya estaba en la sesión con otra versión (leída antes de que otra
        # transacción la confirmara): es un conflicto de versión, no un error interno.
        session.rollback()
        raise VersionConflictError from None

    if model is None:
        session.rollback()
        raise NotFoundError

    if model.version != expected_version:
        session.rollback()
        raise VersionConflictError

    return model


def commit_or_translate(
    session: Session,
    *,
    duplicates: dict[str, Callable[[], CommercialRelationshipError]],
) -> None:
    """Confirma la transacción traduciendo unicidad y versión por nombre de restricción.

    Args:
        session: Sesión activa.
        duplicates: Nombre de restricción → fábrica de la excepción de aplicación
            (con su `field`); se crea una instancia nueva por error.
    """
    try:
        session.commit()

    except IntegrityError as exc:
        session.rollback()
        constraint = _constraint_name(exc)

        for name, error in duplicates.items():
            if constraint == name:
                raise error() from None

        raise

    except StaleDataError:
        session.rollback()
        raise VersionConflictError from None


def end_read(session: Session) -> None:
    """Cierra la transacción implícita de una lectura (no retiene conexiones ni bloqueos).

    Usa `commit` y no `rollback`: con `expire_on_commit=False` los objetos leídos
    conservan sus valores, mientras que un `rollback` los caducaría y el siguiente
    acceso abriría otra transacción. No hay cambios pendientes que confirmar.
    """
    if session.in_transaction():
        session.commit()


def _constraint_name(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)

    return getattr(diag, "constraint_name", None)
