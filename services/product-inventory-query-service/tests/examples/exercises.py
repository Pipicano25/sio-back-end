"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII; T127 y T128).

Datos **ficticios** (crema dental, jarabe y analgésicos en tabletas; ningún NIT, razón social ni dato de DAO), con
identificadores fijos para que la documentación generada sea estable. Operational Context, Commercial
Relationship, Product Catalog e Inventory se simulan con estos datos (Principio IV): todos los usuarios de prueba
son miembros `ACTIVE` de la empresa ficticia.

Cada paso es una consulta (`GET`): `actor` es el usuario que la ejecuta y `save` guarda variables `<NOMBRE>` de la
respuesta para los pasos siguientes.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from product_inventory_query_service.application.ports import BranchInfo, Category, Reference
from tests.fakes import Fakes


def uid(group: str, number: int) -> str:
    return f"d22{group}0000-0000-4000-8000-{number:012d}"


COMPANY = uid("a", 1)
OTHER_COMPANY = uid("a", 99)
PPAL, NORTE, SUR = uid("b", 1), uid("b", 2), uid("b", 3)
OTHER_BRANCH = uid("b", 99)
BRAND = uid("c", 1)
CATEGORY = uid("c", 2)
PRICE_LIST = uid("c", 3)
UNIT = Reference(UUID(uid("d", 1)), "UND", "Unidad")
TABLET = Reference(UUID(uid("d", 2)), "TAB", "Tableta")
BASE = f"/api/v1/companies/{COMPANY}"
IMAGE_BASE = "https://catalogo.ejemplo.test/api/v1/public/product-images"


def _product(number: int, name: str, canonical: str, **options) -> dict:
    return dict(number=number, name=name, canonical=canonical, **options)


PRODUCTS = [
    _product(1, "Crema dental Colgate Triple Acción 100 ml", "COLGATE TRIPLE ACCION 100ML", image=True,
             presentations=[("UND", "Unidad", "1", "4500.00"), ("CJ12", "Caja x 12", "12", None)]),
    _product(2, "Crema dental Colgate Herbal 75 ml", "COLGATE HERBAL 75ML", image=True,
             presentations=[("UND", "Unidad", "1", "3900.00")]),
    _product(3, "Crema dental Colgate Kids 50 ml", "COLGATE KIDS 50ML", image=True,
             presentations=[("UND", "Unidad", "1", "3200.00")]),
    _product(4, "Crema dental Colgate Máxima 150 ml", "COLGATE MAXIMA 150ML", image=False,
             presentations=[("UND", "Unidad", "1", "6100.00")]),
    _product(5, "Jarabe Abrilar 100 ml", "ABRILAR JARABE 100ML", image=True, brand=False,
             presentations=[("FR", "Frasco", "1", "28000.00")]),
    _product(6, "Loratadina 10 mg tabletas", "LORATADINA 10MG", image=False, brand=False, unit=TABLET,
             presentations=[("TAB", "Tableta", "1", None), ("CJ10", "Caja x 10", "10", "8500.00")],
             stock={PPAL: "120", NORTE: "0"}, minimum={PPAL: "150"}),
    _product(7, "Acetaminofén 500 mg tabletas", "ACETAMINOFEN 500MG", image=False, brand=False, unit=TABLET,
             presentations=[("CJ10", "Caja x 10", "10", "4200.00")],
             stock={PPAL: "5", NORTE: "3"}, minimum={PPAL: "5", NORTE: "5"}),
    _product(8, "Ibuprofeno 400 mg tabletas", "IBUPROFENO 400MG", image=False, brand=False, unit=TABLET,
             presentations=[("CJ10", "Caja x 10", "10", None)], stock={PPAL: "0"}, minimum={PPAL: "0"}),
    _product(9, "Servicio de domicilio", "SERVICIO DOMICILIO", image=False, brand=False, control=False,
             presentations=[("SRV", "Servicio", "1", "5000.00")], stock={PPAL: "4"}),
    _product(10, "Antiácido descontinuado", "ANTIACIDO 30 TAB", image=False, brand=False, status="INACTIVE",
             unit=TABLET, presentations=[("CJ30", "Caja x 30", "30", None)], stock={SUR: "9"}),
]

COMMON_DATA = [
    ("Empresa", COMPANY, "Empresa ficticia; todos los usuarios de prueba son miembros `ACTIVE`."),
    ("Sucursal PPAL", PPAL, "Sucursal principal (`ACTIVE`)."),
    ("Sucursal NORTE", NORTE, "Sucursal a la que ningún usuario está asignado: se lee igual (A-08)."),
    ("Sucursal SUR", SUR, "Tercera sucursal (`ACTIVE`)."),
    ("Otra empresa", OTHER_COMPANY, "Empresa de la que ningún usuario de prueba es miembro."),
    ("Sucursal de la otra empresa", OTHER_BRANCH, "Pedirla desde la empresa ficticia responde `404`."),
    ("Marca Colgate (ficticia)", BRAND, "Marca de los productos 1 a 4."),
    ("Lista de precios", PRICE_LIST, "Lista predeterminada de la empresa."),
] + [
    (f"Producto {p['number']}", uid("e", p["number"]), p["name"]) for p in PRODUCTS
]


def seed(fakes: Fakes) -> None:
    """Carga los datos ficticios en los cuatro dobles."""
    company, other = UUID(COMPANY), UUID(OTHER_COMPANY)
    fakes.oc.members.add(company)
    fakes.oc.branch_rows[company] = [BranchInfo(UUID(b), company, "ACTIVE") for b in (PPAL, NORTE, SUR)]
    fakes.oc.branch_rows[other] = [BranchInfo(UUID(OTHER_BRANCH), other, "ACTIVE")]
    for product in PRODUCTS:
        number = product["number"]
        global_id = UUID(uid("f", number))
        summary = fakes.pc.add_product(global_id, product["canonical"],
                                       brand_id=UUID(BRAND) if product.get("brand", True) else None,
                                       has_image=product["image"], categories={UUID(CATEGORY)},
                                       identifiers={f"7700000{number:06d}"}, base_unit=product.get("unit", UNIT))
        # Nombres legibles de marca y categoría, y la URL tal como la construiría PC-1 (referencia firmada opaca).
        fakes.pc.products[global_id] = replace(
            summary,
            brand=Reference(UUID(BRAND), "COLGATE", "Colgate (ficticia)") if summary.brand else None,
            categories=(Category(UUID(CATEGORY), "CUIDADO", "Cuidado personal (ficticia)", True),),
            image_url=f"{IMAGE_BASE}?ref=EJEMPLO-{number:02d}" if product["image"] else None,
        )
        company_product = fakes.cr.add_product(
            company, product["name"], id=UUID(uid("e", number)), global_product_id=global_id,
            internal_code=f"P-{number:04d}", status=product.get("status", "ACTIVE"),
            inventory_control_enabled=product.get("control", True),
        )
        for index, (code, label, factor, price) in enumerate(product["presentations"], start=1):
            info = fakes.pc.add_presentation(global_id, code, label, factor, id=UUID(uid("7", number * 10 + index)))
            row = fakes.cr.add_presentation(company_product, info.id, sku=f"SKU-{number:02d}{index}",
                                            id=UUID(uid("8", number * 10 + index)))
            if price is not None:
                fakes.cr.set_price(row, price, price_list_id=UUID(PRICE_LIST),
                                   price_list_item_id=UUID(uid("9", number * 10 + index)))
        for branch, quantity in product.get("stock", {}).items():
            fakes.inventory.set_balance(company, UUID(branch), company_product.id, quantity)
        for branch, minimum in product.get("minimum", {}).items():
            fakes.inventory.set_policy(company, UUID(branch), company_product.id, minimum)


MINIMUMS = "perm:inventory:product-policies:read"
STOCK = "perm:product-inventory-query:stock:read"


def step(file: str, title: str, actor: str, path: str, expect: int, why: list[str], save: dict | None = None,
         requires: tuple[str, ...] = (), allowed_status: int | None = None) -> dict:
    """`requires`: permisos de bloque que exige además del funcional (un filtro de mínimos, bajo stock).

    `allowed_status`: estado de quien tiene el permiso funcional y los de `requires`, si difiere del del actor.
    """
    return dict(file=file, title=title, actor=actor, method="GET", path=path, expect=expect, why=why, save=save or {},
                requires=list(requires), allowed_status=allowed_status if allowed_status is not None else expect)


EXERCISES = [
    dict(
        number=1,
        folder="1-catalogo-con-imagen-y-precio",
        title="Catálogo con imagen y precio",
        purpose=(
            "Buscar «Colgate» solo con imagen (ruta R-B: Commercial Relationship busca y Product Catalog evalúa la "
            "imagen sobre esos candidatos), en páginas de 2 con cursor, con una presentación sin precio."
        ),
        steps=[
            step("01-primera-pagina.md", "Primera página con imagen", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&has_image=true&page_size=2", 200,
                 ["`search` lo evalúa Commercial Relationship y `has_image` Product Catalog, antes de elegir la página.",
                  "De los 4 «Colgate», 3 tienen imagen: la primera página trae 2, en orden `display_name:asc`, y "
                  "`has_next = true`.",
                  "`image_url` es la URL directa que construye Product Catalog: se usa sin token en `<img src>`.",
                  "`ventas.test` ve precios y existencias, pero no los mínimos."],
                 save={"CURSOR": "next_cursor"}),
            step("02-segunda-pagina.md", "Página siguiente con el cursor", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&has_image=true&page_size=2&cursor=<CURSOR>", 200,
                 ["El cursor continúa después del último producto entregado: ninguno se repite.",
                  "La «Caja x 12» no tiene precio en la lista: `unit_price = null` con `resolution = NO_PRICE_IN_LIST`; "
                  "nunca se usa el precio de otra lista ni se inventa.",
                  "Es la última página: `has_next = false` y `next_cursor = null`."]),
        ],
    ),
    dict(
        number=2,
        folder="2-cambio-de-filtros-y-cursor",
        title="Cambio de filtros y cursor",
        purpose=(
            "Un cursor está ligado a la empresa, al endpoint, a los filtros, al orden y al tamaño de página. Si el "
            "frontend cambia algo y conserva el cursor, la consulta se reinicia sin error; un cursor alterado es "
            "`422`."
        ),
        steps=[
            step("01-primera-pagina.md", "Primera página de «Colgate»", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&page_size=2", 200,
                 ["Primera página de 2; se guarda el cursor."], save={"CURSOR": "next_cursor"}),
            step("02-cambio-de-busqueda.md", "Otra búsqueda con el cursor anterior", "ventas.test",
                 f"{BASE}/product-overviews?search=Abrilar&page_size=2&cursor=<CURSOR>", 200,
                 ["La huella de los filtros cambió: primera página de «Abrilar» con `pagination_reset = true` y "
                  "`FILTERS_CHANGED`."]),
            step("03-cambio-de-tamano.md", "Otro tamaño de página", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&page_size=3&cursor=<CURSOR>", 200,
                 ["`PAGE_SIZE_CHANGED`: primera página de 3."]),
            step("04-cambio-de-orden.md", "Otro orden", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&page_size=2&sort=internal_code:desc&cursor=<CURSOR>", 200,
                 ["`SORT_CHANGED`: primera página en el orden pedido, informado en `sort_applied`."]),
            step("05-cursor-alterado.md", "Cursor alterado", "ventas.test",
                 f"{BASE}/product-overviews?search=Colgate&page_size=2&cursor=v1.eyJ9.firma-alterada", 422,
                 ["La firma no corresponde: `INVALID_CURSOR`, sin resultados y sin decir qué falló."]),
        ],
    ),
    dict(
        number=3,
        folder="3-inventario-multisucursal",
        title="Inventario multisucursal",
        purpose=(
            "Existencias de la Loratadina en toda la empresa y en una sucursal sin usuarios asignados: unidad base, "
            "equivalencias por presentación y diferencia entre saldo cero y sin registro."
        ),
        steps=[
            step("01-consolidado.md", "Consolidado de la empresa", "inventario.test",
                 f"{BASE}/inventory-overviews?search=Loratadina", 200,
                 ["Sin `branch_id` el alcance es `COMPANY`: las tres sucursales activas.",
                  "120 tabletas con la «Caja x 10» son 12 cajas y resto 0: la existencia no se repite por presentación.",
                  "NORTE tiene un saldo registrado en 0 (`REGISTERED`); SUR nunca tuvo saldo (`NOT_REGISTERED`).",
                  "`inventario.test` ve los mínimos: PPAL está bajo su mínimo de 150."]),
            step("02-sucursal-no-asignada.md", "Sucursal sin asignación del usuario", "inventario.test",
                 f"{BASE}/inventory-overviews?search=Loratadina&branch_id={NORTE}", 200,
                 ["Con membresía `ACTIVE` y permiso de lectura se consulta cualquier sucursal de la empresa (A-08)."]),
            step("03-sucursal-de-otra-empresa.md", "Sucursal de otra empresa", "inventario.test",
                 f"{BASE}/inventory-overviews?branch_id={OTHER_BRANCH}", 404,
                 ["La sucursal no es de la empresa de la ruta: `404`, igual que una empresa sin membresía."]),
        ],
    ),
    dict(
        number=4,
        folder="4-bajo-stock",
        title="Productos bajo el mínimo",
        purpose=(
            "Pares producto–sucursal con existencia estrictamente menor que el mínimo activo, del mayor faltante "
            "al menor. Igual al mínimo, mínimo 0 y sin política no aparecen."
        ),
        steps=[
            step("01-todas-las-sucursales.md", "Bajo mínimo en la empresa", "inventario.test",
                 f"{BASE}/low-stock-products", 200, requires=(STOCK, MINIMUMS), why=
                 ["Loratadina en PPAL (120 < 150, faltante 30) y Acetaminofén en NORTE (3 < 5, faltante 2).",
                  "Acetaminofén en PPAL está en su mínimo (5 = 5) e Ibuprofeno tiene mínimo 0: no aparecen.",
                  "Orden predeterminado `shortfall:desc`."]),
            step("02-una-sucursal.md", "Bajo mínimo en una sucursal", "inventario.test",
                 f"{BASE}/low-stock-products?branch_id={NORTE}", 200, ["Solo los pares de NORTE."],
                 requires=(STOCK, MINIMUMS)),
        ],
    ),
    dict(
        number=5,
        folder="5-resumen",
        title="Resumen de inventario",
        purpose=(
            "Indicadores operativos por sucursal y consolidados, cada uno calculado por su propietario: los adoptados "
            "por Commercial Relationship y los de saldo y política por Inventory. El resumen no tiene valoración "
            "económica (fuera del alcance de la spec 022)."
        ),
        steps=[
            step("01-resumen-de-la-empresa.md", "Resumen de la empresa", "inventario.test",
                 f"{BASE}/inventory-summary", 200,
                 ["`adopted_products` cuenta los productos `ACTIVE` con control de inventario (8): excluye el "
                  "servicio (sin control) y el producto inactivo.",
                  "Inventory cuenta por saldo: el servicio y el producto inactivo tienen saldo y sí cuentan con saldo "
                  "positivo; un producto sin registro de saldo no cuenta en ningún indicador.",
                  "Ningún indicador se calcula restando datos de Commercial Relationship e Inventory."]),
            step("02-resumen-de-una-sucursal.md", "Resumen de una sucursal", "supervisor.test",
                 f"{BASE}/inventory-summary?branch_id={NORTE}", 200,
                 ["Solo NORTE; `adopted_products` sigue siendo de la empresa.",
                  "Tampoco `supervisor.test` recibe valoración ni costos: el servicio no los devuelve a nadie."]),
        ],
    ),
    dict(
        number=6,
        folder="6-permisos",
        title="Permisos y bloques visibles",
        purpose=(
            "La misma consulta muestra bloques distintos según los permisos: `ventas` sin mínimos, `inventario` sin "
            "precios, y `compras`, `reportes` y `consulta` sin acceso."
        ),
        steps=[
            step("01-ventas-sin-minimos.md", "Productos para ventas", "ventas.test",
                 f"{BASE}/product-overviews?search=Loratadina", 200,
                 ["`ventas.test` ve precios y existencias (`stock:read`, sin `perm:inventory:balances:read`), pero no "
                  "`minimum_stock` ni `minimum_state`."]),
            step("02-inventario-sin-precios.md", "Productos para inventario", "inventario.test",
                 f"{BASE}/product-overviews?search=Loratadina", 200,
                 ["`inventario.test` no tiene `perm:commercial-relationship:price_list_items:read`: ninguna "
                  "presentación lleva `price`; sí ve los mínimos."]),
            step("03-filtro-no-autorizado.md", "Filtro de mínimos sin el permiso", "ventas.test",
                 f"{BASE}/inventory-overviews?minimum_state=BELOW_MINIMUM", 403,
                 ["`minimum_state` depende del bloque de mínimos, que `ventas.test` no puede ver: `403`.",
                  "Quien sí tiene `perm:inventory:product-policies:read` (`inventario`, `supervisor`, `admin`) "
                  "obtiene `200`."],
                 requires=(MINIMUMS,), allowed_status=200),
            step("04-compras-sin-acceso.md", "Compras no consulta el resumen", "compras.test",
                 f"{BASE}/inventory-summary", 403,
                 ["`compras`, `reportes` y `consulta` no tienen ningún permiso de estas consultas: `403` sin revelar "
                  "el permiso."],
                 allowed_status=200),
        ],
    ),
]
