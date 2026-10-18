"""Juego de datos sintético y determinista del oráculo (T120; research R-16).

- Productos adoptados con nombres repetidos (empates en `display_name` y en `canonical_name`), activos e
  inactivos, con y sin control de inventario, con SKU, códigos de barras, marcas, categorías e imagen.
- Productos globales **no adoptados** por la empresa (PC los conduce y CR debe descartarlos).
- Saldos y políticas en tres sucursales: positivos, cero registrados, sin registro, bajo, igual y sobre el mínimo.

Todo sale de `random.Random(seed)`: con la misma semilla, los mismos datos.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


def _uuid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(128), version=4)


@dataclass
class Product:
    id: UUID
    global_id: UUID
    display_name: str
    canonical_name: str
    internal_code: str
    status: str
    inventory_control_enabled: bool
    skus: tuple[str, ...]
    identifiers: tuple[str, ...]
    brand: UUID | None
    categories: tuple[UUID, ...]
    has_image: bool
    product_type: str


@dataclass
class Dataset:
    company: UUID
    branches: list[UUID]
    brands: list[UUID]
    categories: list[UUID]
    products: list[Product]
    foreign_globals: list[Product]
    """Productos globales que la empresa no adoptó."""
    quantities: dict[tuple[UUID, UUID], Decimal] = field(default_factory=dict)
    """(sucursal, producto) → cantidad registrada (la ausencia es `NOT_REGISTERED`)."""
    minimums: dict[tuple[UUID, UUID], Decimal] = field(default_factory=dict)


NAMES = ("Arroz", "Aceite", "Azúcar", "Café", "Colgate", "Crema", "Jabón", "Leche", "Pasta", "Sal")


def build(seed: int = 22, *, adopted: int = 120, foreign: int = 40) -> Dataset:
    rng = random.Random(seed)
    company = _uuid(rng)
    branches = [_uuid(rng) for _ in range(3)]
    brands = [_uuid(rng) for _ in range(5)]
    categories = [_uuid(rng) for _ in range(6)]

    def product(index: int) -> Product:
        base = rng.choice(NAMES)
        variant = rng.randint(1, 12)  # pocas variantes: muchos nombres repetidos
        return Product(
            id=_uuid(rng),
            global_id=_uuid(rng),
            display_name=f"{base} {variant:02d}",
            canonical_name=f"{base.upper()} {rng.randint(1, 8)}",
            internal_code=f"C{index:04d}",
            status="ACTIVE" if rng.random() < 0.85 else "INACTIVE",
            inventory_control_enabled=rng.random() < 0.9,
            skus=tuple(f"SKU{index:04d}{suffix}" for suffix in "ab"[: rng.randint(0, 2)]),
            identifiers=(f"770{index:07d}",) if rng.random() < 0.7 else (),
            brand=rng.choice(brands) if rng.random() < 0.8 else None,
            categories=tuple(rng.sample(categories, rng.randint(0, 2))),
            has_image=rng.random() < 0.4,
            product_type=rng.choice(("GOOD", "GOOD", "SERVICE")),
        )

    products = [product(index) for index in range(adopted)]
    foreign_globals = [product(adopted + index) for index in range(foreign)]
    data = Dataset(company, branches, brands, categories, products, foreign_globals)

    for item in products:
        for branch in branches:
            roll = rng.random()
            if roll < 0.35:
                data.quantities[(branch, item.id)] = Decimal(rng.randint(1, 30))
            elif roll < 0.5:
                data.quantities[(branch, item.id)] = Decimal(0)
            if rng.random() < 0.3:
                data.minimums[(branch, item.id)] = Decimal(rng.choice((0, 2, 5, 10, 15)))
    return data
