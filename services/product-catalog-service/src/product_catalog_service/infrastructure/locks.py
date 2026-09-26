"""Bloqueos para serializar invariantes que abarcan varias filas o tablas (R-09, R-10)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from product_catalog_service.application.exceptions import NotFoundError
from product_catalog_service.infrastructure.models import GlobalProductModel


def lock_product(session: Session, product_id: UUID) -> GlobalProductModel:
    """Bloquea la fila del producto (`SELECT … FOR UPDATE`) y la devuelve."""
    product = session.execute(
        select(GlobalProductModel)
        .where(GlobalProductModel.id == product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()

    if product is None:
        raise NotFoundError(f"El producto {product_id} no existe.")

    return product


def lock_row(session: Session, model: type, row_id: UUID, *, label: str):
    """Bloquea y devuelve una fila por identificador o lanza `NotFoundError`."""
    row = session.execute(
        select(model)
        .where(model.id == row_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()

    if row is None:
        raise NotFoundError(f"{label} {row_id} no existe.")

    return row


def advisory_lock(session: Session, key: str) -> None:
    """Toma un bloqueo consultivo transaccional sobre una clave de texto."""
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": key},
    )
