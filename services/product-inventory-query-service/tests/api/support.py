"""Constructor de datos ficticios coherentes en los cuatro dobles (empresa, sucursales, productos, existencias).

Un producto de la empresa existe en CR (producto y presentaciones) y en PC (producto global, presentaciones
globales y unidad base); sus saldos y políticas, en Inventory. Los usuarios de prueba son miembros `ACTIVE` de la
empresa (el doble de OC no distingue usuarios: la membresía es de la empresa).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from product_inventory_query_service.application.ports import CompanyPresentation, CompanyProduct, Reference
from tests.fakes import Fakes

UNIT = Reference(UUID("00000000-0000-4000-8000-0000000000aa"), "UND", "Unidad")
TABLET = Reference(UUID("00000000-0000-4000-8000-0000000000ab"), "TAB", "Tableta")
COST_WORDS = ("average_unit_cost", "unit_cost", "cost", "margin", "profit", "fifo")


@dataclass
class Item:
    product: CompanyProduct
    presentations: list[CompanyPresentation]
    global_presentations: list[UUID]

    @property
    def id(self) -> str:
        return str(self.product.id)


@dataclass
class World:
    fakes: Fakes
    company: UUID
    branches: list[UUID]
    other_company: UUID
    other_branches: list[UUID]
    items: list[Item] = field(default_factory=list)

    @classmethod
    def create(cls, fakes: Fakes, *, branches: int = 2) -> "World":
        company, own = fakes.oc.add_company(branches=branches)
        other, foreign = fakes.oc.add_company(member=False, branches=1)
        return cls(fakes, company, own, other, foreign)

    @property
    def base(self) -> str:
        return f"/api/v1/companies/{self.company}"

    def product(self, name: str, *, canonical: str | None = None, presentations: tuple = (("UND", "Unidad", "1"),),
                brand: UUID | None = None, has_image: bool = False, categories: set[UUID] | None = None,
                identifiers: set[str] | None = None, status: str = "ACTIVE", global_status: str = "ACTIVE",
                inventory_control_enabled: bool = True, internal_code: str | None = None,
                skus: tuple[str | None, ...] = (), unit: Reference = UNIT, product_type: str = "GOOD",
                company: UUID | None = None) -> Item:
        global_id = uuid4()
        self.fakes.pc.add_product(global_id, canonical or name.upper(), brand_id=brand, has_image=False,
                                  categories=categories, identifiers=identifiers, status=global_status,
                                  base_unit=unit, product_type=product_type)
        extra = {"internal_code": internal_code} if internal_code else {}
        product = self.fakes.cr.add_product(company or self.company, name, global_product_id=global_id, status=status,
                                            inventory_control_enabled=inventory_control_enabled, **extra)
        rows, globals_ = [], []
        for index, (code, label, factor) in enumerate(presentations):
            info = self.fakes.pc.add_presentation(global_id, code, label, factor)
            sku = skus[index] if index < len(skus) else None
            rows.append(self.fakes.cr.add_presentation(product, info.id, sku=sku))
            globals_.append(info.id)
            if has_image and index == 0:  # spec 024: la imagen es de la presentación (la primera)
                self.fakes.pc.add_image(info.id)
        item = Item(product, rows, globals_)
        self.items.append(item)
        return item

    def stock(self, item: Item, quantity: str, *, branch: int = 0) -> None:
        self.fakes.inventory.set_balance(self.company, self.branches[branch], item.product.id, quantity)

    def minimum(self, item: Item, minimum: str, *, branch: int = 0) -> None:
        self.fakes.inventory.set_policy(self.company, self.branches[branch], item.product.id, minimum)


def walk(client, url: str, *, limit: int = 500) -> tuple[list[dict], list[dict]]:
    """Recorre todas las páginas con `next_cursor`; devuelve los elementos y las respuestas."""
    items, pages, cursor = [], [], None
    for _ in range(limit):
        separator = "&" if "?" in url else "?"
        response = client.get(url + (f"{separator}cursor={cursor}" if cursor else ""))
        assert response.status_code == 200, response.text
        body = response.json()
        pages.append(body)
        items.extend(body["items"])
        if not body["has_next"]:
            assert body["next_cursor"] is None
            return items, pages
        cursor = body["next_cursor"]
    raise AssertionError("el recorrido no terminó")


def keys_in(value) -> set[str]:
    """Todas las claves de un JSON, a cualquier profundidad."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            found |= keys_in(item)
    elif isinstance(value, list):
        for item in value:
            found |= keys_in(item)
    return found
