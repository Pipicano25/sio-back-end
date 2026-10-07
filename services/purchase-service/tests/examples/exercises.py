"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII; T067).

Datos **ficticios** (no existe una fuente del sistema anterior para compras): identificadores
fijos y reloj fijo (`NOW`) para que la documentación generada sea estable.

Cada paso:

- `actor`: usuario de prueba que ejecuta la llamada;
- `kind`: `"accion"` (escritura: usuario humano con permiso, membresía y asignación a la
  sucursal) o `"consulta"` (permiso y membresía);
- `headers`: cabeceras adicionales (`Idempotency-Key`);
- `before`: cambios en los dobles antes del paso (`inventory_down`, `inventory_up`,
  `consume:<VARIABLE>`), para mostrar fallas de Inventory sin servicios reales;
- `save`: variables `<NOMBRE>` que se guardan de la respuesta y se usan después.
"""

from __future__ import annotations

from datetime import UTC, datetime

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
"""Reloj de los ejercicios: 5 de noviembre de 2026 (10:00 en Bogotá)."""

COMPANY = "d14a0000-0000-4000-8000-000000000001"
OTHER_COMPANY = "d14a0000-0000-4000-8000-000000000099"
BRANCH = "d14b0000-0000-4000-8000-000000000001"
BRANCH_B = "d14b0000-0000-4000-8000-000000000002"
SUPPLIER = "d14c0000-0000-4000-8000-000000000001"
ORGANIZATION = "d14c0000-0000-4000-8000-000000000002"
CONDITION = "d14c0000-0000-4000-8000-000000000003"
CREDIT_TYPE = "d14c0000-0000-4000-8000-000000000004"
ARROZ = "d14d0000-0000-4000-8000-000000000001"
ACEITE = "d14d0000-0000-4000-8000-000000000002"
SERVICIO = "d14d0000-0000-4000-8000-000000000003"
GLOBAL_ARROZ = "d14d0000-0000-4000-8000-000000000011"
GLOBAL_ACEITE = "d14d0000-0000-4000-8000-000000000012"
CAJA = "d14e0000-0000-4000-8000-000000000001"
GLOBAL_CAJA = "d14e0000-0000-4000-8000-000000000011"
SUPPLIER_PRODUCT = "d14e0000-0000-4000-8000-000000000021"
UNIT = "d14e0000-0000-4000-8000-000000000031"
MISSING = "d14f0000-0000-4000-8000-000000000404"

ACCION = "accion"
CONSULTA = "consulta"

COMMON_DATA = [
    ("Empresa", COMPANY, "Empresa ficticia (moneda COP); todos los usuarios de prueba son miembros `ACTIVE`."),
    ("Sucursal principal", BRANCH, "Bodega ficticia; todos los usuarios de prueba están asignados a ella."),
    ("Proveedor", SUPPLIER, "Distribuidora Ficticia S.A.S. (`ACTIVE`), identificada como NIT 900123456."),
    ("Condición de pago", CONDITION, "Crédito a 30 días en COP del proveedor."),
    ("Arroz 500 g", ARROZ, "Producto con control de inventario (código 000045); unidad base `UND`."),
    ("Caja x12", CAJA, "Presentación de compra del arroz: 12 unidades base."),
    ("Aceite 1 L", ACEITE, "Producto con control de inventario (código 000046)."),
    ("Servicio de transporte", SERVICIO, "Producto **sin** control de inventario (no se puede comprar en esta fase)."),
]

P = f"/api/v1/companies/{COMPANY}"


def draft(operation_date: str, *lines: dict, **extra) -> dict:
    body = {"branch_id": BRANCH, "company_supplier_id": SUPPLIER, "operation_date": operation_date, "lines": list(lines)}
    body.update(extra)
    return body


def ln(product: str, quantity: str, unit_cost: str, **extra) -> dict:
    return {"company_product_id": product, "quantity": quantity, "unit_cost": unit_cost, **extra}


def key(name: str) -> dict:
    return {"Idempotency-Key": name}


SEQUENCE = {"series_code": "PRINCIPAL", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "MONTHLY"}

CREATE_SEQUENCE = {
    "file": "01-crear-la-secuencia.md",
    "title": "Crear la secuencia mensual de la empresa",
    "actor": "compras.test",
    "kind": ACCION,
    "method": "POST",
    "path": f"{P}/purchase-sequences",
    "body": SEQUENCE,
    "expect": 201,
    "save": {"SECUENCIA": "id"},
    "why": [
        "Sin una secuencia activa ninguna compra puede confirmarse.",
        "`MONTHLY` lleva un contador independiente por año-mes de la fecha de la compra.",
    ],
}


def create_draft(file: str, title: str, body: dict, variable: str, why: list[str], expect: int = 201) -> dict:
    step = {
        "file": file,
        "title": title,
        "actor": "compras.test",
        "kind": ACCION,
        "method": "POST",
        "path": f"{P}/purchases",
        "body": body,
        "expect": expect,
        "why": why,
    }
    if expect == 201:
        step["save"] = {variable: "id"}
    return step


def confirm(file: str, title: str, variable: str, version: int, idempotency: str, why: list[str], expect: int = 200, save=None, before=None) -> dict:
    step = {
        "file": file,
        "title": title,
        "actor": "compras.test",
        "kind": ACCION,
        "method": "POST",
        "path": f"{P}/purchases/<{variable}>/confirmation",
        "body": {"version": version},
        "headers": key(idempotency),
        "expect": expect,
        "why": why,
    }
    if save:
        step["save"] = save
    if before:
        step["before"] = before
    return step


EXERCISES = [
    {
        "number": 1,
        "folder": "1-secuencias",
        "title": "Secuencias de numeración",
        "purpose": (
            "El comprador configura la numeración de compras de la empresa: una secuencia mensual, su consulta "
            "con contadores por período y el rechazo de una segunda secuencia activa en el mismo alcance."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            {
                "file": "02-consultar-las-secuencias.md",
                "title": "Consultar las secuencias de la empresa",
                "actor": "compras.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{P}/purchase-sequences",
                "expect": 200,
                "why": ["Los contadores por período aparecen cuando se confirma la primera compra del período."],
            },
            {
                "file": "03-segunda-secuencia-activa.md",
                "title": "Intentar una segunda secuencia activa",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchase-sequences",
                "body": {**SEQUENCE, "series_code": "ALTERNA", "prefix": "CA"},
                "expect": 409,
                "why": [
                    "A lo sumo una secuencia activa por empresa, sucursal y tipo de documento (P-02).",
                    "Para cambiar de secuencia se desactiva primero la vigente.",
                ],
            },
        ],
    },
    {
        "number": 2,
        "folder": "2-borrador",
        "title": "Compra en borrador",
        "purpose": (
            "El comprador registra una compra en borrador con una línea en caja de 12, agrega otra línea, "
            "y ve los rechazos de versión vieja, de producto sin control de inventario y de proveedor inexistente."
        ),
        "data": COMMON_DATA,
        "steps": [
            create_draft(
                "01-crear-el-borrador.md",
                "Crear la compra en borrador",
                draft("2026-11-04", ln(ARROZ, "2", "120000", company_product_presentation_id=CAJA, tax_amount="45600"),
                      supplier_payment_condition_id=CONDITION, supplier_document_number="FV-1001"),
                "COMPRA",
                [
                    "El borrador no afecta inventario y no tiene número.",
                    "La cantidad y el costo van en la unidad de compra (caja); el servidor calcula subtotal, total, "
                    "cantidad en unidad base (24) y costo por unidad base sin impuestos (10000).",
                    "Los nombres e identificación se guardan como snapshots provisionales.",
                ],
            ),
            {
                "file": "02-agregar-una-linea.md",
                "title": "Agregar una línea",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/details",
                "body": {**ln(ACEITE, "6", "9800", discount_amount="800"), "version": 1},
                "expect": 201,
                "why": ["Cada cambio de líneas exige la `version` vigente y la incrementa."],
            },
            {
                "file": "03-version-vieja.md",
                "title": "Agregar otra línea con una versión vieja",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/details",
                "body": {**ln(ACEITE, "1", "9800"), "version": 1},
                "expect": 409,
                "why": ["La compra ya está en la versión 2: el cliente debe volver a consultarla."],
            },
            {
                "file": "04-producto-sin-control-de-inventario.md",
                "title": "Agregar un producto sin control de inventario",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/details",
                "body": {**ln(SERVICIO, "1", "50000"), "version": 2},
                "expect": 409,
                "why": [
                    "El producto existe, pero su configuración impide comprarlo: toda compra confirmada genera "
                    "entrada en Inventory (P-01). Existe pero no es apto → `409`.",
                ],
            },
            create_draft(
                "05-proveedor-inexistente.md",
                "Crear una compra con un proveedor inexistente",
                {**draft("2026-11-04"), "company_supplier_id": MISSING},
                "",
                ["Referencia inexistente o no resoluble → `422` (P-03)."],
                expect=422,
            ),
            {
                "file": "06-consultar-el-borrador.md",
                "title": "Consultar el borrador",
                "actor": "compras.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{P}/purchases/<COMPRA>",
                "expect": 200,
                "why": ["Las lecturas exigen permiso y membresía; no exigen asignación a la sucursal."],
            },
        ],
    },
    {
        "number": 3,
        "folder": "3-confirmacion",
        "title": "Confirmación idempotente",
        "purpose": (
            "La confirmación ingresa la mercancía en Inventory y asigna el número del período. Inventory no responde "
            "en el primer intento: la operación queda pendiente y el reintento con la misma clave la completa sin "
            "duplicar la entrada; repetirla de nuevo devuelve el mismo resultado."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft(
                "02-crear-el-borrador.md",
                "Crear la compra en borrador",
                draft("2026-11-04", ln(ARROZ, "2", "120000", company_product_presentation_id=CAJA, tax_amount="45600")),
                "COMPRA",
                ["Compra de contado (sin condición): `due_date` = fecha de la compra."],
            ),
            confirm(
                "03-confirmar-con-inventory-caido.md",
                "Confirmar mientras Inventory no responde",
                "COMPRA",
                1,
                "confirmar-compra-0001",
                [
                    "La operación queda `PENDING` (el `operation_id` se informa) y la compra sigue en borrador sin número.",
                    "Repetir con la **misma** clave completa la operación; el conciliador también lo haría.",
                ],
                expect=503,
                before=["inventory_down"],
            ),
            confirm(
                "04-reintentar-con-la-misma-clave.md",
                "Reintentar con la misma clave",
                "COMPRA",
                1,
                "confirmar-compra-0001",
                [
                    "Inventory recibe la misma clave de operación: aplica la entrada una sola vez.",
                    "La compra queda `CONFIRMED` con `CP-202611-000001`.",
                ],
                save={"ENTRADA": "inventory_operation_id"},
                before=["inventory_up"],
            ),
            confirm(
                "05-repetir-la-confirmacion.md",
                "Repetir la confirmación (respuesta perdida)",
                "COMPRA",
                1,
                "confirmar-compra-0001",
                ["Misma clave: mismo resultado, sin una segunda entrada ni un segundo número."],
            ),
            {
                "file": "06-consultar-las-operaciones.md",
                "title": "Consultar las operaciones de la compra",
                "actor": "compras.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{P}/purchases/<COMPRA>/operations",
                "expect": 200,
                "why": ["La clave de idempotencia nunca se expone; `inventory_operation_id` identifica la entrada."],
            },
        ],
    },
    {
        "number": 4,
        "folder": "4-compra-retroactiva",
        "title": "Compra retroactiva",
        "purpose": (
            "Con numeración mensual, una compra de octubre confirmada en noviembre continúa el contador de octubre "
            "en lugar de rechazarse."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-compra-de-noviembre.md", "Compra de noviembre", draft("2026-11-03", ln(ACEITE, "1", "9800")), "NOVIEMBRE", ["Fecha de negocio en noviembre."]),
            confirm("03-confirmar-noviembre.md", "Confirmar la compra de noviembre", "NOVIEMBRE", 1, "retro-0001", ["Primer número de noviembre: `CP-202611-000001`."]),
            create_draft("04-compra-de-octubre.md", "Compra de octubre registrada tarde", draft("2026-10-20", ln(ACEITE, "2", "9800")), "OCTUBRE", ["La fecha de negocio pertenece a octubre."]),
            confirm(
                "05-confirmar-octubre.md",
                "Confirmar la compra de octubre en noviembre",
                "OCTUBRE",
                1,
                "retro-0002",
                ["`operation_date` determina el período: continúa el contador de octubre → `CP-202610-000001`."],
            ),
        ],
    },
    {
        "number": 5,
        "folder": "5-anulacion",
        "title": "Anulación",
        "purpose": (
            "Anular un borrador es local; anular una compra confirmada revierte exactamente su entrada en Inventory; "
            "si esas unidades ya se consumieron, la anulación se rechaza y la compra sigue confirmada."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-borrador-a-anular.md", "Borrador que se anulará", draft("2026-11-04", ln(ACEITE, "1", "9800")), "BORRADOR", ["Compra registrada por error."]),
            {
                "file": "03-anular-el-borrador.md",
                "title": "Anular el borrador",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<BORRADOR>/cancellation",
                "body": {"version": 1, "reason": "Registrada por error"},
                "headers": key("anular-0001"),
                "expect": 200,
                "why": ["Un borrador se anula sin Inventory; no se borra físicamente."],
            },
            create_draft("04-compra-a-anular.md", "Compra que se confirmará y anulará", draft("2026-11-04", ln(ARROZ, "1", "120000", company_product_presentation_id=CAJA)), "COMPRA", ["Una caja de 12 unidades."]),
            confirm("05-confirmar.md", "Confirmar la compra", "COMPRA", 1, "anular-0002", ["Ingresa 12 unidades del arroz."], save={"ENTRADA": "inventory_operation_id"}),
            {
                "file": "06-anular-la-compra-confirmada.md",
                "title": "Anular la compra confirmada",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/cancellation",
                "body": {"version": 3, "reason": "Mercancía rechazada"},
                "headers": key("anular-0003"),
                "expect": 200,
                "why": [
                    "Purchase pide a Inventory el reverso de exactamente `inventory_operation_id`.",
                    "La compra conserva su número y queda `CANCELLED`.",
                ],
            },
            create_draft("07-compra-vendida.md", "Otra compra", draft("2026-11-04", ln(ACEITE, "3", "9800")), "VENDIDA", ["Sus unidades se venderán antes de anular."]),
            confirm("08-confirmar-la-otra.md", "Confirmar la otra compra", "VENDIDA", 1, "anular-0004", ["Ingresa 3 unidades del aceite."], save={"ENTRADA_VENDIDA": "inventory_operation_id"}),
            {
                "file": "09-anular-con-inventario-consumido.md",
                "title": "Anular cuando sus unidades ya se vendieron",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<VENDIDA>/cancellation",
                "body": {"version": 3, "reason": "Error de precio"},
                "headers": key("anular-0005"),
                "before": ["consume:ENTRADA_VENDIDA"],
                "expect": 409,
                "why": [
                    "Inventory responde `ENTRY_LAYER_CONSUMED`: la compra sigue `CONFIRMED`.",
                    "Primero se anulan las ventas que consumieron las unidades, o se registra un ajuste.",
                ],
            },
        ],
    },
    {
        "number": 6,
        "folder": "6-hitos",
        "title": "Hitos logísticos",
        "purpose": (
            "El comprador registra los hitos de abastecimiento, ve el rechazo de un hito fuera de orden y consulta la "
            "línea de tiempo con los intervalos y el lead time total."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-crear-la-compra.md", "Crear la compra", draft("2026-11-01", ln(ACEITE, "4", "9800")), "COMPRA", ["Pedido formalizado el 1 de noviembre."]),
            *[
                {
                    "file": file,
                    "title": title,
                    "actor": "compras.test",
                    "kind": ACCION,
                    "method": "POST",
                    "path": f"{P}/purchases/<COMPRA>/lifecycle-events",
                    "body": {"event_type": event, "occurred_at": moment, "source": source},
                    "expect": expect,
                    "why": why,
                }
                for file, title, event, moment, source, expect, why in [
                    ("03-pedido.md", "Registrar el pedido", "ORDERED", "2026-11-01T14:00:00Z", "USER", 201, ["Inicio del lead time."]),
                    ("04-llegada-fuera-de-orden.md", "Registrar una llegada anterior al pedido", "ARRIVED", "2026-11-01T10:00:00Z", "USER", 422, ["El orden temporal debe respetar ORDERED ≤ … ≤ AVAILABLE_FOR_SALE."]),
                    ("05-despacho.md", "Registrar el despacho del proveedor", "SUPPLIER_DISPATCHED", "2026-11-02T14:00:00Z", "SUPPLIER", 201, ["Lo informa el proveedor."]),
                    ("06-llegada.md", "Registrar la llegada", "ARRIVED", "2026-11-03T14:00:00Z", "USER", 201, ["Mercancía en el punto de recepción."]),
                ]
            ],
            confirm("07-confirmar.md", "Confirmar la compra", "COMPRA", 1, "hitos-0001", ["La recepción y la disponibilidad exigen una compra confirmada."]),
            {
                "file": "08-recepcion.md",
                "title": "Registrar la recepción",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/lifecycle-events",
                "body": {"event_type": "RECEIVED", "occurred_at": "2026-11-03T16:00:00Z", "source": "USER"},
                "expect": 201,
                "why": ["Los hitos son inmutables: un error se corrige registrando otro del mismo tipo."],
            },
            {
                "file": "09-disponible.md",
                "title": "Registrar la disponibilidad para la venta",
                "actor": "compras.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/purchases/<COMPRA>/lifecycle-events",
                "body": {"event_type": "AVAILABLE_FOR_SALE", "occurred_at": "2026-11-04T14:00:00Z", "source": "USER"},
                "expect": 201,
                "why": ["Fin del lead time total."],
            },
            {
                "file": "10-linea-de-tiempo.md",
                "title": "Consultar la línea de tiempo",
                "actor": "compras.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{P}/purchases/<COMPRA>/lifecycle-events",
                "expect": 200,
                "why": ["Los intervalos se calculan al leer; nunca se escriben en Commercial Relationship."],
            },
        ],
    },
    {
        "number": 7,
        "folder": "7-consultas",
        "title": "Consultas",
        "purpose": "Listado filtrado de compras de la empresa y aislamiento: otra empresa responde `404` sin revelar existencia.",
        "data": COMMON_DATA + [("Otra empresa", OTHER_COMPANY, "Empresa ficticia en la que ningún usuario de prueba es miembro.")],
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-compra.md", "Crear una compra", draft("2026-11-04", ln(ACEITE, "1", "9800")), "COMPRA", ["Compra de ejemplo."]),
            confirm("03-confirmar.md", "Confirmar la compra", "COMPRA", 1, "consultas-0001", ["Para consultarla por número."]),
            {
                "file": "04-listar-confirmadas.md",
                "title": "Listar las compras confirmadas",
                "actor": "reportes.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{P}/purchases?status=CONFIRMED&number=CP-202611-000001",
                "expect": 200,
                "why": ["Filtros por estado, sucursal, proveedor, fechas y número; orden estable."],
            },
            {
                "file": "05-otra-empresa.md",
                "title": "Consultar una compra desde otra empresa",
                "actor": "reportes.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{OTHER_COMPANY}/purchases/<COMPRA>",
                "expect": 404,
                "why": ["Sin membresía en esa empresa: `404`, igual que un recurso inexistente."],
            },
        ],
    },
]
