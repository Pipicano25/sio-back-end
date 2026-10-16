"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII; T073).

Datos **ficticios** (no existe una fuente del sistema anterior para ventas): identificadores
fijos y reloj fijo (`NOW`) para que la documentación generada sea estable.

Cada paso:

- `actor`: usuario de prueba que ejecuta la llamada;
- `kind`: `"accion"` (escritura: usuario humano con permiso, membresía y asignación a la
  sucursal) o `"consulta"` (permiso y membresía);
- `headers`: cabeceras adicionales (`Idempotency-Key`);
- `before`: cambios en los dobles antes del paso (`inventory_down`, `inventory_up`,
  `price:<valor>` para el precio de la unidad de arroz en la lista predeterminada, `stock:<cantidad>` para las existencias del
  arroz con costo conocido, `unknown_cost:<cantidad>` para existencias de apertura sin costo);
- `save`: variables `<NOMBRE>` que se guardan de la respuesta y se usan después.
"""

from __future__ import annotations

from datetime import UTC, datetime

NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
"""Reloj de los ejercicios: 5 de noviembre de 2026 (10:00 en Bogotá)."""

COMPANY = "d15a0000-0000-4000-8000-000000000001"
OTHER_COMPANY = "d15a0000-0000-4000-8000-000000000099"
BRANCH = "d15b0000-0000-4000-8000-000000000001"
BRANCH_B = "d15b0000-0000-4000-8000-000000000002"
CUSTOMER = "d15c0000-0000-4000-8000-000000000001"
CUSTOMER_ORG = "d15c0000-0000-4000-8000-000000000002"
PERSON = "d15c0000-0000-4000-8000-000000000011"
ORGANIZATION = "d15c0000-0000-4000-8000-000000000012"
ARROZ = "d15d0000-0000-4000-8000-000000000001"
ACEITE = "d15d0000-0000-4000-8000-000000000002"
SERVICIO = "d15d0000-0000-4000-8000-000000000003"
GLOBAL_ARROZ = "d15d0000-0000-4000-8000-000000000011"
GLOBAL_ACEITE = "d15d0000-0000-4000-8000-000000000012"
CAJA = "d15e0000-0000-4000-8000-000000000001"
GLOBAL_CAJA = "d15e0000-0000-4000-8000-000000000011"
UNIT = "d15e0000-0000-4000-8000-000000000031"
PAYMENT_METHOD = "d15c0000-0000-4000-8000-000000000021"
INACTIVE_PAYMENT_METHOD = "d15c0000-0000-4000-8000-000000000022"
LISTA = "d15f0000-0000-4000-8000-000000000001"
LISTA_2 = "d15f0000-0000-4000-8000-000000000002"
ITEM_CAJA = "d15f0000-0000-4000-8000-000000000011"
ITEM_ACEITE = "d15f0000-0000-4000-8000-000000000012"
# Spec 019: toda venta por presentación; la unidad base, con su presentación de factor 1.
UNIDAD_ARROZ = "d15e0000-0000-4000-8000-000000000002"
UNIDAD_ACEITE = "d15e0000-0000-4000-8000-000000000003"
UNIDAD_SERVICIO = "d15e0000-0000-4000-8000-000000000004"
GLOBAL_UNIDAD_ARROZ = "d15e0000-0000-4000-8000-000000000012"
GLOBAL_UNIDAD_ACEITE = "d15e0000-0000-4000-8000-000000000013"
LISTA_GENERAL = "d15f0000-0000-4000-8000-000000000003"
ITEM_UNIDAD_ARROZ = "d15f0000-0000-4000-8000-000000000013"
ITEM_UNIDAD_ACEITE = "d15f0000-0000-4000-8000-000000000014"
ITEM_UNIDAD_SERVICIO = "d15f0000-0000-4000-8000-000000000015"
ITEM_CAJA_GENERAL = "d15f0000-0000-4000-8000-000000000016"
ITEM_UNIDAD_ARROZ_NUEVO = "d15f0000-0000-4000-8000-000000000017"
MISSING = "d15f0000-0000-4000-8000-000000000404"

ACCION = "accion"
CONSULTA = "consulta"

COMMON_DATA = [
    ("Empresa", COMPANY, "Empresa ficticia (moneda COP); todos los usuarios de prueba son miembros `ACTIVE`."),
    ("Sucursal principal", BRANCH, "Almacén ficticio en Bogotá; todos los usuarios de prueba están asignados a ella."),
    ("Cliente persona", CUSTOMER, "Ana Ficticia Pérez (`ACTIVE`), identificada como CC 1020304050."),
    ("Cliente organización", CUSTOMER_ORG, "Tiendas Ficticias S.A.S. (`ACTIVE`), identificada como NIT 900123456."),
    ("Medio de pago", PAYMENT_METHOD, "Efectivo (`CASH`, `ACTIVE`) en Payment Reference: referencia declarativa, no un pago (spec 020)."),
    ("Arroz 500 g", ARROZ, "Vendible, con control de inventario; 1000 unidades a costo 1000."),
    ("Unidad de arroz", UNIDAD_ARROZ, "Presentación de factor 1 del arroz (toda venta indica su presentación)."),
    ("Caja x12", CAJA, "Presentación de venta del arroz: 12 unidades base."),
    ("Aceite 1 L", ACEITE, "Vendible, con control de inventario; 1000 unidades a costo 6000."),
    ("Unidad de aceite", UNIDAD_ACEITE, "Presentación de factor 1 del aceite."),
    ("Servicio de instalación", SERVICIO, "Vendible pero **sin** control de inventario (no se puede vender en esta fase)."),
    ("Lista de precios general (predeterminada)", LISTA_GENERAL, "Unidad de arroz a 1500, caja x12 a 18000 y unidad de aceite a 9000: cada presentación con su precio explícito."),
    ("Lista de precios mayorista", LISTA, "Caja x12 del arroz a 16000; unidad de aceite a 8500."),
    ("Lista de precios temporada", LISTA_2, "Sin precios para estos productos."),
]

P = f"/api/v1/companies/{COMPANY}"
PROFITABILITY_NOTE = (
    "`ventas.test`, `reportes.test` y `consulta.test` no tienen `perm:sales:sales:read-profitability`: en sus "
    "respuestas no aparecen costo, `cost_known`, margen ni `has_unknown_cost`."
)


def draft(*lines: dict, **extra) -> dict:
    body = {"branch_id": BRANCH, "company_customer_id": CUSTOMER, "payment_method_id": PAYMENT_METHOD, "lines": list(lines)}
    body.update(extra)
    return body


def ln(product: str, quantity: str, **extra) -> dict:
    """Línea de venta; sin presentación indicada usa la unidad (factor 1) del producto (spec 019)."""
    presentation = extra.pop("company_product_presentation_id", {ARROZ: UNIDAD_ARROZ, ACEITE: UNIDAD_ACEITE, SERVICIO: UNIDAD_SERVICIO}.get(product))
    return {"company_product_id": product, "company_product_presentation_id": presentation, "quantity": quantity, **extra}


def key(name: str) -> dict:
    return {"Idempotency-Key": name}


SEQUENCE = {"series_code": "PRINCIPAL", "prefix": "FV", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "MONTHLY"}

CREATE_SEQUENCE = {
    "file": "01-crear-la-secuencia.md",
    "title": "Crear la secuencia mensual de la empresa",
    "actor": "ventas.test",
    "kind": ACCION,
    "method": "POST",
    "path": f"{P}/sale-sequences",
    "body": SEQUENCE,
    "expect": 201,
    "save": {"SECUENCIA": "id"},
    "why": [
        "Sin una secuencia activa ninguna venta puede confirmarse.",
        "`MONTHLY` lleva un contador independiente por año-mes de la fecha de la venta (la del día en que se confirma).",
    ],
}


def create_draft(file: str, title: str, body: dict, variable: str, why: list[str], expect: int = 201, save=None, before=None) -> dict:
    step = {
        "file": file,
        "title": title,
        "actor": "ventas.test",
        "kind": ACCION,
        "method": "POST",
        "path": f"{P}/sales",
        "body": body,
        "expect": expect,
        "why": why,
    }
    if expect == 201:
        step["save"] = {variable: "id", **(save or {})}
    if before:
        step["before"] = before
    return step


def confirm(file: str, title: str, variable: str, version: int, idempotency: str, why: list[str], expect: int = 200, save=None, before=None) -> dict:
    step = {
        "file": file,
        "title": title,
        "actor": "ventas.test",
        "kind": ACCION,
        "method": "POST",
        "path": f"{P}/sales/<{variable}>/confirmation",
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


def consult(file: str, title: str, actor: str, path: str, why: list[str], expect: int = 200) -> dict:
    return {"file": file, "title": title, "actor": actor, "kind": CONSULTA, "method": "GET", "path": path, "expect": expect, "why": why}


EXERCISES = [
    {
        "number": 1,
        "folder": "1-secuencias",
        "title": "Secuencias de numeración",
        "purpose": (
            "El vendedor configura la numeración de ventas de la empresa: una secuencia mensual, su consulta "
            "con contadores por período y el rechazo de una segunda secuencia activa en el mismo alcance."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            consult(
                "02-consultar-las-secuencias.md",
                "Consultar las secuencias de la empresa",
                "ventas.test",
                f"{P}/sale-sequences",
                ["Los contadores por período aparecen cuando se confirma la primera venta del período."],
            ),
            {
                "file": "03-segunda-secuencia-activa.md",
                "title": "Intentar una segunda secuencia activa",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sale-sequences",
                "body": {**SEQUENCE, "series_code": "ALTERNA", "prefix": "VA"},
                "expect": 409,
                "why": [
                    "A lo sumo una secuencia activa por empresa, sucursal y tipo de documento.",
                    "Para cambiar de secuencia se desactiva primero la vigente.",
                ],
            },
        ],
    },
    {
        "number": 2,
        "folder": "2-borrador-y-precios",
        "title": "Venta en borrador y precios",
        "purpose": (
            "El vendedor registra una venta en borrador: una línea en caja con la lista mayorista y otra con el "
            "precio de su presentación en la lista predeterminada. El precio siempre lo resuelve el sistema: se rechazan el precio manual, "
            "una lista inexistente, una lista sin precio para el producto y un producto sin control de inventario."
        ),
        "data": COMMON_DATA,
        "steps": [
            create_draft(
                "01-crear-el-borrador.md",
                "Crear la venta en borrador",
                draft(ln(ARROZ, "2", company_product_presentation_id=CAJA, price_list_id=LISTA),
                      ln(ACEITE, "3")),
                "VENTA",
                [
                    "La primera línea pide la lista mayorista: precio de la caja 16000 (`price_list_requested = true`).",
                    "La segunda no pide lista: se usa el precio de la unidad de aceite en la lista predeterminada GENERAL (9000).",
                    "Solo contado: `CASH`, sin plazo, `due_date` = `operation_date` = hoy en la zona de la sucursal.",
                    "El borrador no afecta inventario y no tiene número.",
                    "Spec 021 (provisional): no se suma impuesto; el precio de la lista es el importe final "
                    "(`tax_amount` solo admite 0, `TAX_NOT_ALLOWED`). No es una solución fiscal.",
                ],
            ),
            {
                "file": "02-agregar-una-linea.md",
                "title": "Agregar una caja con el precio de la lista predeterminada",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ARROZ, "1", company_product_presentation_id=CAJA), "version": 1},
                "expect": 201,
                "why": [
                    "Sin lista pedida se usa el precio explícito de la caja en la lista predeterminada GENERAL: 18000.0000 (spec 019: sin conversiones entre presentaciones).",
                    "Cada cambio de líneas exige la `version` vigente y la incrementa.",
                ],
            },
            {
                "file": "03-precio-manual.md",
                "title": "Intentar un precio manual",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ACEITE, "1", unit_price="5000"), "version": 2},
                "expect": 422,
                "why": ["Sin precio manual en el MVP (DS-11): `UNIT_PRICE_NOT_ALLOWED`."],
            },
            {
                "file": "03a-impuesto-adicional.md",
                "title": "Intentar sumar un impuesto sobre el precio",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ACEITE, "1", tax_amount="1710"), "version": 2},
                "expect": 422,
                "why": [
                    "Spec 021 (provisional): el precio de la lista es el importe final que paga el cliente; Sales no "
                    "suma impuestos (`TAX_NOT_ALLOWED`). No es una solución fiscal: no separa el impuesto incluido ni "
                    "factura electrónicamente.",
                ],
            },
            {
                "file": "04-lista-inexistente.md",
                "title": "Pedir una lista de precios inexistente",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ACEITE, "1", price_list_id=MISSING), "version": 2},
                "expect": 422,
                "why": ["Commercial Relationship responde que no es aplicable; Sales consulta la lista: no existe → `422 PRICE_LIST_NOT_FOUND` (P-03)."],
            },
            {
                "file": "05-lista-sin-precio.md",
                "title": "Pedir una lista sin precio para el producto",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ACEITE, "1", price_list_id=LISTA_2), "version": 2},
                "expect": 409,
                "why": ["La lista existe pero no tiene precio para el aceite: `409 PRICE_NOT_IN_LIST` (sin respaldo ni conversiones; spec 019)."],
            },
            {
                "file": "06-producto-sin-control-de-inventario.md",
                "title": "Agregar un producto sin control de inventario",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(SERVICIO, "1"), "version": 2},
                "expect": 409,
                "why": ["Toda venta confirmada genera una salida de inventario: el producto existe pero no es apto → `409`."],
            },
            {
                "file": "07-version-vieja.md",
                "title": "Agregar una línea con una versión vieja",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/details",
                "body": {**ln(ACEITE, "1"), "version": 1},
                "expect": 409,
                "why": ["La venta ya está en la versión 2: el cliente debe volver a consultarla."],
            },
            consult(
                "08-consultar-el-borrador.md",
                "Consultar el borrador",
                "ventas.test",
                f"{P}/sales/<VENTA>",
                ["Las lecturas exigen permiso y membresía; no exigen asignación a la sucursal.", PROFITABILITY_NOTE],
            ),
        ],
    },
    {
        "number": 3,
        "folder": "3-disponibilidad",
        "title": "Disponibilidad antes de confirmar",
        "purpose": (
            "El vendedor consulta si hay existencias para el borrador. Las líneas del mismo producto se suman en "
            "unidad base; la consulta no reserva."
        ),
        "data": COMMON_DATA,
        "steps": [
            create_draft(
                "01-crear-el-borrador.md",
                "Crear un borrador con dos líneas de arroz",
                draft(ln(ARROZ, "2", company_product_presentation_id=CAJA), ln(ARROZ, "2"), ln(ACEITE, "1")),
                "VENTA",
                ["2 cajas (24 unidades) y 2 unidades del mismo arroz: 26 unidades base."],
                before=["stock:20"],
            ),
            consult(
                "02-consultar-la-disponibilidad.md",
                "Consultar la disponibilidad",
                "ventas.test",
                f"{P}/sales/<VENTA>/availability",
                [
                    "El arroz requiere 26 y hay 20 en la sucursal: `is_available = false`; el aceite alcanza.",
                    "Es informativa: confirmar sigue validándose contra Inventory, que es la barrera real.",
                ],
            ),
        ],
    },
    {
        "number": 4,
        "folder": "4-confirmacion",
        "title": "Confirmación: precio cambiado e idempotencia",
        "purpose": (
            "La confirmación vuelve a verificar el precio: si cambió, se rechaza sin efectos y el vendedor actualiza "
            "la línea. Luego Inventory no responde: la operación queda pendiente y el reintento con la misma clave "
            "la completa sin duplicar la salida; repetirla de nuevo devuelve el mismo resultado."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft(
                "02-crear-el-borrador.md",
                "Crear la venta en borrador",
                draft(ln(ARROZ, "4")),
                "VENTA",
                ["Precio de la unidad de arroz en la lista predeterminada: 1500."],
                save={"LINEA": "lines[0].id"},
            ),
            confirm(
                "03-confirmar-con-precio-cambiado.md",
                "Confirmar después de un cambio de precio",
                "VENTA",
                1,
                "confirmar-venta-0001",
                [
                    "El precio de la unidad de arroz en la lista predeterminada pasó a 1550: `409 PRICES_CHANGED` con el valor guardado y el vigente.",
                    "Sin salida, sin número y sin cambios en el borrador.",
                ],
                expect=409,
                before=["price:1550.00"],
            ),
            {
                "file": "04-actualizar-la-linea.md",
                "title": "Actualizar la línea con el precio vigente",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{P}/sales/<VENTA>/details/<LINEA>",
                "body": {**ln(ARROZ, "4"), "version": 1},
                "expect": 200,
                "why": ["Editar la línea vuelve a resolver su precio (1550)."],
            },
            confirm(
                "05-confirmar-con-inventory-caido.md",
                "Confirmar mientras Inventory no responde",
                "VENTA",
                2,
                "confirmar-venta-0002",
                [
                    "La operación queda `PENDING` (el `operation_id` se informa) y la venta sigue en borrador sin número.",
                    "Repetir con la **misma** clave completa la operación; el conciliador también lo haría.",
                ],
                expect=503,
                before=["inventory_down"],
            ),
            confirm(
                "06-reintentar-con-la-misma-clave.md",
                "Reintentar con la misma clave",
                "VENTA",
                2,
                "confirmar-venta-0002",
                [
                    "Inventory recibe la misma clave de operación: aplica la salida una sola vez.",
                    "La venta queda `CONFIRMED` con `FV-202611-000001` y la fecha del día (5 de noviembre).",
                ],
                before=["inventory_up"],
            ),
            confirm(
                "07-repetir-la-confirmacion.md",
                "Repetir la confirmación (respuesta perdida)",
                "VENTA",
                2,
                "confirmar-venta-0002",
                ["Misma clave: mismo resultado, sin una segunda salida ni un segundo número."],
            ),
            consult(
                "08-consultar-las-operaciones.md",
                "Consultar las operaciones de la venta",
                "ventas.test",
                f"{P}/sales/<VENTA>/operations",
                ["La primera clave quedó sin operación (el rechazo fue previo); la segunda, `SUCCEEDED`."],
            ),
        ],
    },
    {
        "number": 5,
        "folder": "5-existencias-insuficientes",
        "title": "Existencias insuficientes",
        "purpose": "Vender más de lo que hay en la sucursal se rechaza completo: ni salida ni número.",
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-crear-el-borrador.md", "Vender 6 unidades de arroz", draft(ln(ARROZ, "6"), ln(ACEITE, "1")), "VENTA",
                         ["Solo hay 5 unidades de arroz en la sucursal."], before=["stock:5"]),
            confirm(
                "03-confirmar.md",
                "Confirmar la venta",
                "VENTA",
                1,
                "existencias-0001",
                [
                    "`409 INSUFFICIENT_STOCK` con el faltante por producto y líneas (disponible y requerido).",
                    "La venta se confirma completa o no se confirma: la línea del aceite tampoco descuenta.",
                ],
                expect=409,
            ),
        ],
    },
    {
        "number": 6,
        "folder": "6-rentabilidad",
        "title": "Rentabilidad y costo desconocido",
        "purpose": (
            "Al confirmar, la venta guarda el costo FIFO que informa Inventory (por unidad base) y el margen. Solo "
            "quien tiene `perm:sales:sales:read-profitability` los ve. Con unidades de apertura sin costo histórico la "
            "venta se confirma igual, sin margen y con el indicador `has_unknown_cost`."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-crear-la-venta.md", "Vender 3 unidades de arroz", draft(ln(ARROZ, "3")), "VENTA", ["3 × 1500 = 4500."]),
            confirm("03-confirmar.md", "Confirmar la venta", "VENTA", 1, "rentabilidad-0001",
                    ["Inventory descuenta 3 unidades a costo FIFO 1000.", PROFITABILITY_NOTE]),
            consult("04-consultar-como-vendedor.md", "Consultar como vendedor", "ventas.test", f"{P}/sales/<VENTA>",
                    ["Sin costo ni margen en la respuesta (se omiten, no aparecen como nulos)."]),
            consult(
                "05-consultar-como-supervisor.md",
                "Consultar como supervisor",
                "supervisor.test",
                f"{P}/sales/<VENTA>",
                [
                    "`supervisor.test` tiene `perm:sales:sales:read-profitability`: costo 1000.0000 por unidad base, "
                    "costo total 3000.00, margen 1500.00 (33.3333 %).",
                ],
            ),
            create_draft("06-venta-con-costo-desconocido.md", "Vender unidades de apertura sin costo", draft(ln(ARROZ, "2")),
                         "APERTURA", ["Las existencias del arroz son unidades de apertura sin costo histórico."],
                         before=["unknown_cost:10"]),
            confirm("07-confirmar.md", "Confirmar la venta", "APERTURA", 1, "rentabilidad-0002",
                    ["Se confirma: `cost_known = false`, márgenes nulos y `has_unknown_cost = true` (C-03)."]),
            consult("08-consultar-como-supervisor.md", "Consultar como supervisor", "supervisor.test", f"{P}/sales/<APERTURA>",
                    ["El margen no se inventa: queda nulo cuando el costo no es conocido."]),
        ],
    },
    {
        "number": 7,
        "folder": "7-anulacion",
        "title": "Anulación",
        "purpose": (
            "Anular un borrador es local; anular una venta confirmada revierte exactamente su salida en Inventory y "
            "restituye las unidades con su costo."
        ),
        "data": COMMON_DATA,
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-borrador-a-anular.md", "Borrador que se anulará", draft(ln(ACEITE, "1")), "BORRADOR", ["Venta registrada por error."]),
            {
                "file": "03-anular-el-borrador.md",
                "title": "Anular el borrador",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<BORRADOR>/cancellation",
                "body": {"version": 1, "reason": "Registrada por error"},
                "headers": key("anular-0001"),
                "expect": 200,
                "why": ["Un borrador se anula sin Inventory; no se borra físicamente."],
            },
            create_draft("04-venta-a-anular.md", "Venta que se confirmará y anulará", draft(ln(ARROZ, "1", company_product_presentation_id=CAJA)), "VENTA", ["Una caja de 12 unidades."]),
            confirm("05-confirmar.md", "Confirmar la venta", "VENTA", 1, "anular-0002", ["Descuenta 12 unidades del arroz."]),
            {
                "file": "06-anular-la-venta-confirmada.md",
                "title": "Anular la venta confirmada",
                "actor": "ventas.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{P}/sales/<VENTA>/cancellation",
                "body": {"version": 3, "reason": "Cliente desistió de la compra"},
                "headers": key("anular-0003"),
                "expect": 200,
                "why": [
                    "Sales pide a Inventory el reverso de exactamente `inventory_operation_id`: vuelven las 12 unidades con su costo.",
                    "La venta conserva número, precio, costo y margen, y queda `CANCELLED`.",
                ],
            },
        ],
    },
    {
        "number": 8,
        "folder": "8-consultas",
        "title": "Consultas",
        "purpose": "Listado filtrado de ventas de la empresa y aislamiento: otra empresa responde `404` sin revelar existencia.",
        "data": COMMON_DATA + [("Otra empresa", OTHER_COMPANY, "Empresa ficticia en la que ningún usuario de prueba es miembro.")],
        "steps": [
            CREATE_SEQUENCE,
            create_draft("02-venta.md", "Crear una venta a una organización", draft(ln(ACEITE, "1"), company_customer_id=CUSTOMER_ORG), "VENTA", ["Venta de ejemplo."]),
            confirm("03-confirmar.md", "Confirmar la venta", "VENTA", 1, "consultas-0001", ["Para consultarla por número."]),
            consult(
                "04-listar-confirmadas.md",
                "Listar las ventas confirmadas",
                "reportes.test",
                f"{P}/sales?status=CONFIRMED&number=FV-202611-000001",
                ["Filtros por estado, sucursal, cliente, fechas y número; orden estable.", PROFITABILITY_NOTE],
            ),
            consult(
                "05-otra-empresa.md",
                "Consultar una venta desde otra empresa",
                "reportes.test",
                f"/api/v1/companies/{OTHER_COMPANY}/sales/<VENTA>",
                ["Sin membresía en esa empresa: `404`, igual que un recurso inexistente."],
                expect=404,
            ),
        ],
    },
]
