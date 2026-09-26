"""Utilidades de persistencia compartidas por los repositorios SQLAlchemy.

Traducen errores de la base a excepciones de aplicación sin filtrar detalles
del motor (Principio XII) y aplican el control de versión esperado
(Principio VII).
"""

from typing import TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from party_identity_service.application.exceptions import (
    NotFoundError,
    PartyIdentityError,
    VersionConflictError,
)

ModelT = TypeVar("ModelT")


def load_for_update(
    session: Session,
    model_class: type[ModelT],
    entity_id: UUID,
    *,
    expected_version: int,
    not_found_message: str,
) -> ModelT:
    """Carga la fila con bloqueo y comprueba la versión esperada.

    Raises:
        NotFoundError: Si la fila no existe.
        VersionConflictError: Si la versión no coincide.
    """
    model = session.get(
        model_class,
        entity_id,
        with_for_update=True,
        populate_existing=True,
    )

    if model is None:
        session.rollback()
        raise NotFoundError(not_found_message)

    if model.version != expected_version:
        session.rollback()
        raise VersionConflictError

    return model


def commit_or_translate(
    session: Session,
    *,
    duplicates: dict[str, type[PartyIdentityError]],
) -> None:
    """Confirma la transacción traduciendo unicidad y versión.

    Args:
        session: Sesión activa.
        duplicates: Nombre de restricción → excepción de aplicación.

    Raises:
        La excepción asociada a la restricción violada, o
        `VersionConflictError` si otra operación cambió la fila.
    """
    try:
        session.commit()

    except IntegrityError as exc:
        session.rollback()
        constraint = _constraint_name(exc)

        for name, error in duplicates.items():
            if constraint == name:
                raise error from None

        raise

    except StaleDataError:
        session.rollback()
        raise VersionConflictError from None


def _constraint_name(exc: IntegrityError) -> str | None:
    diag = getattr(exc.orig, "diag", None)

    return getattr(diag, "constraint_name", None)
