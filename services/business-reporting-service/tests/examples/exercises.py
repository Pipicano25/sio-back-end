"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII).

Datos **ficticios** (analgésicos, jarabe y crema dental; ningún NIT, razón social ni dato de DAO) con
identificadores fijos para que la documentación sea estable. Operational Context, Sales, Purchase, Inventory,
Commercial Relationship y Product Catalog se simulan (Principio IV): las agregaciones son las que devolverían los
propietarios, y cada doble exige el permiso de lectura del propietario sobre el token del usuario (DR-07).

Cada paso es una consulta (`GET`): `actor` la ejecuta; `requires` lista los permisos **del propietario** que también
necesita el usuario; `kind = "csv"` muestra el inicio del archivo descargado.
"""

from __future__ import annotations

from uuid import UUID

from business_reporting_service.application.ports import (
    BranchInfo,
    BranchSales,
    CompanyInfo,
    CompanyProductInfo,
    PresentationSales,
    ProductSales,
    PurchaseRow,
    SalesTotal,
    StockEvolution,
    UnitInfo,
)
from tests.fakes import D, Fakes, USERS as FAKE_USERS


def uid(group: str, number: int) -> str:
    return f"d23{group}0000-0000-4000-8000-{number:012d}"


COMPANY = uid("a", 1)
PPAL, NORTE = uid("b", 1), uid("b", 2)
TABLET = UnitInfo(UUID(uid("d", 1)), "TAB", "Tableta")
ML = UnitInfo(UUID(uid("d", 2)), "ML", "Mililitro")
UNIT = UnitInfo(UUID(uid("d", 3)), "UND", "Unidad")
BASE = f"/api/v1/companies/{COMPANY}/reports"
BRANCH_BASE = f"/api/v1/companies/{COMPANY}/branches/{PPAL}/reports"
PERIOD = "date_from=2026-10-01&date_to=2026-10-15"

SALES_READ = "perm:sales:sales:read"
PURCHASES_READ = "perm:purchase:purchases:read"
STOCK_EVOLUTION_READ = "perm:inventory:stock_evolution:read"
CR_PRODUCTS = "perm:commercial-relationship:company_products:read"
PC_PRODUCTS = "perm:product-catalog:products:read"
OC = ["perm:operational-context:application_users:read", "perm:operational-context:branches:read"]

PRODUCTS = {
    1: ("A-500", "Acetaminofén 500 mg tabletas", TABLET),
    2: ("J-120", "Jarabe para la tos 120 ml", ML),
    3: ("C-100", "Crema dental 100 ml", UNIT),
}

COMMON_DATA = [
    "Empresa ficticia `<EMPRESA>` (`" + COMPANY + "`, zona `America/Bogota`, moneda `COP`) con dos sucursales "
    "activas: Principal `PPAL` (`" + PPAL + "`) y Norte `NORTE` (`" + NORTE + "`).",
    "Productos ficticios: " + "; ".join(f"`{code}` {name} (unidad base `{unit.code}`)" for code, name, unit in
                                         PRODUCTS.values()) + ".",
    "Todos los usuarios de prueba son miembros `ACTIVE` de la empresa. Hoy es 2026-10-18 en Bogotá.",
    "Las cifras son las agregaciones que devolverían Sales, Purchase e Inventory: el servicio de reportes no las "
    "recalcula a partir de documentos.",
]


def product_id(number: int) -> UUID:
    return UUID(uid("e", number))


def seed(fakes: Fakes) -> None:
    fakes.company = CompanyInfo(UUID(COMPANY), "America/Bogota", "COP")
    fakes.branches = [BranchInfo(UUID(PPAL), UUID(COMPANY), "PPAL", "Principal", "ACTIVE", "America/Bogota"),
                      BranchInfo(UUID(NORTE), UUID(COMPANY), "NORTE", "Norte", "ACTIVE", "America/Bogota")]
    fakes.members = {f"sub-{name}" for name in FAKE_USERS}
    for number, (code, name, unit) in PRODUCTS.items():
        global_id = UUID(uid("f", number))
        fakes.products[product_id(number)] = CompanyProductInfo(product_id(number), global_id, code, name)
        fakes.units[global_id] = unit
    fakes.product_sales = [
        ProductSales(product_id(2), "J-120", "Jarabe para la tos 120 ml", "COP", D("2400"), D("380000"), 19, [
            PresentationSales(UUID(uid("c", 3)), "FR", "Frasco 120 ml", D("20"), D("2400"), D("380000"))]),
        ProductSales(product_id(1), "A-500", "Acetaminofén 500 mg tabletas", "COP", D("1250"), D("612500"), 84, [
            PresentationSales(UUID(uid("c", 1)), "CJ10", "Caja x 10", D("100"), D("1000"), D("490000")),
            PresentationSales(UUID(uid("c", 2)), "TAB", "Tableta", D("250"), D("250"), D("122500"))]),
        ProductSales(product_id(3), "C-100", "Crema dental 100 ml", "COP", D("40"), D("180000"), 31, [
            PresentationSales(UUID(uid("c", 4)), "UND", "Unidad", D("40"), D("40"), D("180000"))]),
    ]
    fakes.sales_totals = [SalesTotal("COP", D("1172500"), 120)]
    fakes.branch_sales = [BranchSales(UUID(PPAL), "COP", 80, D("820750")), BranchSales(UUID(NORTE), "COP", 40, D("351750"))]
    from datetime import date, datetime

    fakes.purchases = [
        PurchaseRow(UUID(uid("9", 1)), date(2026, 10, 3), datetime.fromisoformat("2026-10-04T15:20:00+00:00"),
                    UUID(PPAL), "Distribuidora Ficticia del Cauca", "Dato ficticio", "OC-000101", "FV-3301", "CONFIRMED",
                    "RECEIVED", "RECEIVED", "COP", D("1450000")),
        PurchaseRow(UUID(uid("9", 2)), date(2026, 10, 9), None, UUID(NORTE), "Laboratorio Ficticio S.A.S.",
                    "Dato ficticio", "OC-000102", None, "CONFIRMED", "PENDING_RECEIPT", "PENDING", "COP", D("620000")),
        PurchaseRow(UUID(uid("9", 3)), date(2026, 10, 12), None, UUID(PPAL), "Distribuidora Ficticia del Cauca",
                    "Dato ficticio", "OC-000103", None, "CANCELLED", "CANCELLED", None, "COP", D("300000")),
    ]
    fakes.evolution[UUID(PPAL)] = [
        StockEvolution(product_id(1), D("400"), D("1000"), D("900"), D("0"), D("20"), D("5"), D("2"), D("523"), 41),
        StockEvolution(product_id(2), D("600"), D("2400"), D("1800"), D("120"), D("0"), D("0"), D("0"), D("1080"), 22),
    ]
    fakes.evolution[UUID(NORTE)] = [
        StockEvolution(product_id(1), D("150"), D("300"), D("280"), D("0"), D("0"), D("0"), D("10"), D("160"), 18),
    ]


def step(file: str, title: str, path: str, *, actor: str, requires: list[str], why: list[str], kind: str = "json",
         expect: int = 200, allowed_status: int = 200) -> dict:
    return dict(file=file, title=title, method="GET", path=path, actor=actor, requires=requires, why=why, kind=kind,
                expect=expect, allowed_status=allowed_status, save={})


EXERCISES = [
    dict(number=1, folder="1-productos-mas-vendidos", title="Productos más vendidos", data=[
        "Tres productos con unidades base distintas: el ranking por cantidad compara unidades distintas y la respuesta "
        "lo advierte con `mixed_base_units`.",
    ], order=["Primero el ranking predeterminado (por cantidad) y después por importe con el desglose por "
              "presentación: son independientes."], steps=[
        step("01-ranking-por-cantidad.md", "Ranking por cantidad en unidad base", f"{BASE}/top-selling-products?{PERIOD}",
             actor="reportes.test", requires=[SALES_READ, CR_PRODUCTS, PC_PRODUCTS, *OC], why=[
                 "Sin `rank_by`: se ordena por cantidad vendida en la unidad base de cada producto (DR-04).",
                 "Solo ventas `CONFIRMED` por `operation_date`; las anuladas no cuentan (DR-01).",
                 "`mixed_base_units = true`: el jarabe (ml) y las tabletas no son comparables entre sí; nunca se "
                 "suman cantidades de productos distintos."]),
        step("02-ranking-por-importe.md", "Ranking por importe con presentaciones",
             f"{BASE}/top-selling-products?{PERIOD}&rank_by=amount&include_presentations=true&limit=2",
             actor="ventas.test", requires=[SALES_READ, CR_PRODUCTS, PC_PRODUCTS, *OC], why=[
                 "`rank_by=amount` ordena por importe dentro de la moneda.",
                 "`include_presentations=true` muestra cómo se agrupan las presentaciones en la unidad base con el "
                 "factor guardado en cada venta (Caja x 10 → 10 tabletas)."]),
    ]),
    dict(number=2, folder="2-ventas-por-sucursal", title="Ventas por sucursal", data=[
        "Principal 80 ventas por 820 750 COP y Norte 40 por 351 750 COP.",
    ], order=["Un solo paso."], steps=[
        step("01-comparar-sucursales.md", "Comparar las sucursales de la empresa", f"{BASE}/sales-by-branch?{PERIOD}",
             actor="reportes.test", requires=[SALES_READ, *OC], why=[
                 "Sin `branch_id`: todas las sucursales activas; las que no venden aparecen con cero.",
                 "`share_percentage` es la participación sobre el total de la empresa en la misma moneda."]),
    ]),
    dict(number=3, folder="3-compras-del-periodo", title="Compras del período", data=[
        "Una compra recibida, una pendiente de recepción y una anulada.",
    ], order=["Primero todas las compras con sus totales; después solo las pendientes: los totales no cambian "
              "porque son del período completo."], steps=[
        step("01-compras-y-totales.md", "Compras con sus totales por categoría", f"{BASE}/purchases?{PERIOD}",
             actor="compras.test", requires=[PURCHASES_READ, *OC], why=[
                 "`effective_total` = recibidas + pendientes; la anulada se informa y no suma (DR-03).",
                 "La pendiente no es mercancía recibida: tiene su propio total.",
                 "`received_at` es informativa; el período es por `operation_date` (DR-02)."]),
        step("02-solo-pendientes.md", "Solo las pendientes de recepción",
             f"{BASE}/purchases?{PERIOD}&category=PENDING_RECEIPT", actor="reportes.test",
             requires=[PURCHASES_READ, *OC], why=["El filtro de categoría cambia las filas, no los totales."]),
    ]),
    dict(number=4, folder="4-evolucion-de-existencias", title="Evolución de existencias de una sucursal", data=[
        "Sucursal Principal: acetaminofén y jarabe con entradas, salidas, reversos y ajustes; sucursal Norte: "
        "acetaminofén.",
    ], order=["Pasos independientes: primero la sucursal principal (su UUID va en la ruta) y después la empresa "
              "consolidada."], steps=[
        step("01-sucursal-principal.md", "Evolución en la sucursal principal", f"{BRANCH_BASE}/stock-evolution?{PERIOD}",
             actor="reportes.test", requires=[STOCK_EVOLUTION_READ, CR_PRODUCTS, PC_PRODUCTS, *OC], why=[
                 "Cantidades en la unidad base de cada producto; **sin costos**: `stock_evolution:read` no abre el "
                 "kardex (DR-11).",
                 "`final = inicial + entradas − salidas − reversos de entrada + reversos de salida + ajustes "
                 "positivos − ajustes negativos`; el servicio lo verifica en cada fila.",
                 "Los días se cuentan en la zona horaria de la sucursal (`criteria.from` y `criteria.to`)."]),
            step("02-consolidada-de-la-empresa.md", "Evolución consolidada de la empresa", f"{BASE}/stock-evolution?{PERIOD}",
             actor="reportes.test", requires=[STOCK_EVOLUTION_READ, CR_PRODUCTS, PC_PRODUCTS, *OC], why=[
                 "Ruta de empresa: Inventory suma **por producto** las sucursales (INV-R1C, una consulta por página); "
                 "nunca suma productos distintos.",
                 "El acetaminofén aparece con `branch_count = 2` (Principal y Norte); el jarabe, con 1.",
                 "Los días se cuentan en la zona horaria de la empresa; sin costos."]),
]),
    dict(number=6, folder="6-reportes-por-sucursal", title="Reportes de una sucursal", data=[
        "Mismos datos que los ejercicios 1 a 3; la sucursal Norte (`" + NORTE + "`).",
    ], order=["Pasos independientes: las rutas `/branches/{branch_id}/reports/…` consultan solo esa sucursal."], steps=[
        step("01-ventas-de-la-sucursal.md", "Ventas de la sucursal Norte",
             f"/api/v1/companies/{COMPANY}/branches/{NORTE}/reports/sales-by-branch?{PERIOD}", actor="reportes.test",
             requires=[SALES_READ, *OC], why=[
                 "Solo la sucursal de la ruta, también si no vendió (fila en cero).",
                 "Sin `share_percentage`: con una sola sucursal no hay comparación; la participación está en la ruta "
                 "de la empresa (sobre las sucursales de la respuesta)."]),
        step("02-compras-de-la-sucursal.md", "Compras de la sucursal Norte",
             f"/api/v1/companies/{COMPANY}/branches/{NORTE}/reports/purchases?{PERIOD}", actor="compras.test",
             requires=[PURCHASES_READ, *OC], why=[
                 "Mismo resultado que la ruta de la empresa con `branch_id` de Norte; `totals` es de esa sucursal.",
                 "`branch_id` por consulta no se admite en esta ruta (`422`)."]),
    ]),
    dict(number=5, folder="5-descarga-csv", title="Descarga en CSV", data=[
        "Mismos datos que el ejercicio 3.",
    ], order=["Un solo paso."], steps=[
        step("01-compras-en-csv.md", "Compras del período en CSV", f"{BASE}/purchases?{PERIOD}&format=csv",
             actor="compras.test", requires=[PURCHASES_READ, *OC], kind="csv", why=[
                 "`format=csv`: mismos filtros, permisos y datos que el JSON, en UTF-8 con BOM.",
                 "Las filas `TOTAL …` van al final; la última fila `TOTAL FILAS` solo aparece si el archivo está "
                 "completo.",
                 "El texto que empieza por `=`, `+`, `-` o `@` se escribe con `'` delante (protección de fórmulas)."]),
    ]),
]
