"""Ejercicios de `docs/ejemplo/` como datos estructurados (Principio XXII).

Datos **ficticios** (no existe una fuente del sistema anterior para movimientos de
inventario): identificadores fijos para que la documentación generada sea estable.

Cada paso:

- `actor`: `"operador"` (cuenta de servicio `inventory-test-operator`) o un usuario de prueba;
- `kind`: `"operacion"` (solo cuentas de servicio) o `"consulta"` (permiso + alcance);
- `save`: variables `<NOMBRE>` que se guardan de la respuesta y se usan en pasos posteriores.
"""

from __future__ import annotations

COMPANY = "d44a0000-0000-4000-8000-000000000001"
OTHER_COMPANY = "d44a0000-0000-4000-8000-000000000099"
BRANCH = "d44b0000-0000-4000-8000-000000000001"
USER = "d44c0000-0000-4000-8000-000000000001"
ARROZ = "d44d0000-0000-4000-8000-000000000001"
ACEITE = "d44d0000-0000-4000-8000-000000000002"
SERVICIO = "d44d0000-0000-4000-8000-000000000003"
"""Producto empresarial sin control de inventario (`inventory_control_enabled = false`)."""

PURCHASE_DOC = "d44e0000-0000-4000-8000-000000000001"
SALE_DOC = "d44e0000-0000-4000-8000-000000000002"

OPERACION = "operacion"
CONSULTA = "consulta"

COMMON_DATA = [
    ("Empresa", COMPANY, "Empresa ficticia; todos los usuarios de prueba son miembros `ACTIVE`."),
    ("Sucursal", BRANCH, "Bodega principal ficticia (`ACTIVE`)."),
    ("Usuario operativo", USER, "Usuario de la empresa que confirmó el documento en Purchase o Sales."),
    ("Arroz 500 g", ARROZ, "Producto empresarial con control de inventario; unidad base: unidad."),
    ("Aceite 1 L", ACEITE, "Producto empresarial con control de inventario; unidad base: unidad."),
    ("Servicio de domicilio", SERVICIO, "Producto empresarial **sin** control de inventario."),
]


def uid(group: str, number: int) -> str:
    return f"d44f{group}00-0000-4000-8000-{number:012d}"


def operation(key: int, origin_type: str, document: str, *lines: dict, reason: str | None = None) -> dict:
    return {
        "operation_key": uid("01", key),
        "company_id": COMPANY,
        "branch_id": BRANCH,
        "origin_type": origin_type,
        "origin_id": document,
        "application_user_id": USER,
        "correlation_id": uid("02", key),
        "reason": reason,
        "lines": list(lines),
    }


def ln(number: int, product: str, quantity: str, unit_cost: str | None = None) -> dict:
    item = {"origin_detail_id": uid("03", number), "company_product_id": product, "quantity": quantity}
    if unit_cost is not None:
        item["unit_cost"] = unit_cost
    return item


def reversal(key: int, reason: str, company: str = COMPANY) -> dict:
    return {
        "operation_key": uid("01", key),
        "company_id": company,
        "application_user_id": USER,
        "correlation_id": uid("02", key),
        "reason": reason,
    }


BASE = f"/api/v1/companies/{COMPANY}/branches/{BRANCH}"

ENTRY_10_ARROZ_5_ACEITE = operation(
    1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10", "2500.50"), ln(2, ACEITE, "5.5", "9800")
)

EXERCISES = [
    {
        "number": 1,
        "folder": "1-entradas-de-compra",
        "title": "Entradas de compra",
        "purpose": (
            "Purchase confirma una compra y aplica su entrada en Inventory con su identidad técnica: "
            "una entrada de dos líneas con costo, su repetición idempotente, una clave reutilizada con "
            "otro contenido y un producto sin control de inventario."
        ),
        "data": COMMON_DATA + [("Compra", PURCHASE_DOC, "Documento ficticio de Purchase (`origin_id`).")],
        "steps": [
            {
                "file": "01-aplicar-una-entrada.md",
                "title": "Aplicar la entrada de una compra",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": ENTRY_10_ARROZ_5_ACEITE,
                "expect": 201,
                "save": {"OP_ENTRADA": "id"},
                "why": [
                    "`operation_key` lo genera Purchase (su operación de confirmación) y lo conserva en los reintentos.",
                    "Las cantidades van en unidad base, como cadena decimal con a lo sumo 4 decimales.",
                    "`unit_cost` es obligatorio (valoración FIFO, 013): cada línea crea una capa de costo.",
                    "La primera entrada de un producto en la sucursal crea su saldo.",
                ],
            },
            {
                "file": "02-repetir-la-entrada.md",
                "title": "Repetir la misma entrada (respuesta perdida)",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": ENTRY_10_ARROZ_5_ACEITE,
                "expect": 200,
                "why": [
                    "Misma clave, mismo cliente y misma solicitud: Inventory devuelve el resultado original.",
                    "No vuelve a consultar Operational Context ni Commercial Relationship ni cambia saldos.",
                ],
            },
            {
                "file": "03-misma-clave-otra-cantidad.md",
                "title": "Reutilizar la clave con otra cantidad",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "11", "2500.50"), ln(2, ACEITE, "5.5", "9800")),
                "expect": 409,
                "why": [
                    "La huella de la solicitud cambia: nunca se devuelve en silencio el resultado anterior.",
                    "El consumidor debe usar una clave nueva para una solicitud nueva.",
                ],
            },
            {
                "file": "04-producto-sin-control-de-inventario.md",
                "title": "Entrada de un producto sin control de inventario",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(2, "PURCHASE", PURCHASE_DOC, ln(3, SERVICIO, "1", "1200")),
                "expect": 422,
                "why": [
                    "Commercial Relationship informa `inventory_control_enabled = false`: el producto no admite movimientos.",
                    "La operación se rechaza completa; no se aplica ninguna línea.",
                ],
            },
        ],
    },
    {
        "number": 2,
        "folder": "2-salidas-de-venta",
        "title": "Salidas de venta",
        "purpose": (
            "Sales confirma una venta y aplica su salida: una salida con saldo suficiente, una salida "
            "rechazada por saldo insuficiente (sin aplicar ninguna línea) y una salida con costo."
        ),
        "data": COMMON_DATA + [("Venta", SALE_DOC, "Documento ficticio de Sales (`origin_id`).")],
        "steps": [
            {
                "file": "01-entrada-inicial.md",
                "title": "Entrada inicial de 10 unidades de arroz",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10", "2500.50")),
                "expect": 201,
                "why": ["Prepara el saldo de la sucursal para las salidas (una capa de 10 a 2 500,50)."],
            },
            {
                "file": "02-aplicar-una-salida.md",
                "title": "Aplicar la salida de una venta",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(2, "SALE", SALE_DOC, ln(2, ARROZ, "3")),
                "expect": 201,
                "why": [
                    "El saldo baja de 10 a 7 y el movimiento registra saldo anterior y nuevo.",
                    "Las salidas no llevan costo.",
                ],
            },
            {
                "file": "03-saldo-insuficiente.md",
                "title": "Salida con una línea sin saldo suficiente",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(3, "SALE", SALE_DOC, ln(3, ARROZ, "2"), ln(4, ACEITE, "1")),
                "expect": 409,
                "why": [
                    "El aceite no tiene saldo: la operación completa se rechaza y el arroz tampoco se descuenta.",
                    "`shortages` indica cada línea afectada con lo disponible y lo pedido.",
                    "El saldo nunca queda negativo, tampoco con ventas simultáneas.",
                ],
            },
            {
                "file": "04-salida-con-costo.md",
                "title": "Salida que informa un costo",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(4, "SALE", SALE_DOC, ln(5, ARROZ, "1", "2500")),
                "expect": 422,
                "why": ["Solo las entradas de compra aceptan `unit_cost`."],
            },
        ],
    },
    {
        "number": 3,
        "folder": "3-reversos",
        "title": "Reversos",
        "purpose": (
            "Purchase y Sales anulan documentos confirmados revirtiendo la operación completa con "
            "`company_id` obligatorio: reverso de una entrada cuya capa ya se consumió, reverso de una salida, "
            "reverso repetido y reverso pedido desde otra empresa."
        ),
        "data": COMMON_DATA + [("Compra", PURCHASE_DOC, "Documento ficticio de Purchase."), ("Venta", SALE_DOC, "Documento ficticio de Sales.")],
        "steps": [
            {
                "file": "01-entrada.md",
                "title": "Entrada de 10 unidades de arroz",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10", "2500.50")),
                "expect": 201,
                "save": {"OP_ENTRADA": "id"},
                "why": ["Operación que luego se intentará revertir."],
            },
            {
                "file": "02-salida.md",
                "title": "Salida de 4 unidades",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(2, "SALE", SALE_DOC, ln(2, ARROZ, "4")),
                "expect": 201,
                "save": {"OP_SALIDA": "id"},
                "why": ["Deja un saldo de 6, menor que la entrada de 10."],
            },
            {
                "file": "03-reverso-de-entrada-sin-saldo.md",
                "title": "Revertir la entrada cuando ya se vendió parte",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
                "body": reversal(3, "Anulación de la compra ficticia"),
                "expect": 409,
                "why": [
                    "La capa de la entrada ya entregó 4 unidades a la venta: se rechaza con "
                    "`ENTRY_LAYER_CONSUMED` sin cambios (013, DS-16).",
                    "La corrección es anular antes la venta (paso 4) o registrar un ajuste.",
                ],
            },
            {
                "file": "04-reverso-de-salida.md",
                "title": "Revertir la salida",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs/<OP_SALIDA>/reversal",
                "body": reversal(4, "Anulación de la venta ficticia"),
                "expect": 201,
                "why": [
                    "`company_id` es obligatorio: la operación original se busca solo dentro de esa empresa.",
                    "Se crea un `OUTPUT_REVERSAL` enlazado al movimiento original y el saldo vuelve a 10.",
                    "No se vuelven a validar sucursal ni producto; el usuario operativo sí (puede estar inactivo).",
                ],
            },
            {
                "file": "05-reverso-repetido.md",
                "title": "Revertir otra vez la misma salida con otra clave",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs/<OP_SALIDA>/reversal",
                "body": reversal(5, "Segundo intento de anulación"),
                "expect": 409,
                "why": ["Una operación se revierte a lo sumo una vez (`ALREADY_REVERSED`)."],
            },
            {
                "file": "06-reverso-desde-otra-empresa.md",
                "title": "Pedir el reverso con el company_id de otra empresa",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
                "body": reversal(6, "Intento desde otra empresa", company=OTHER_COMPANY),
                "expect": 404,
                "why": ["La operación no existe en esa empresa: `404` idéntico al de una operación inexistente."],
            },
            {
                "file": "07-reverso-de-entrada.md",
                "title": "Revertir la entrada con saldo suficiente",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
                "body": reversal(7, "Anulación de la compra ficticia"),
                "expect": 201,
                "why": [
                    "Con la venta revertida, la capa de la entrada vuelve a estar completa: el reverso la retira "
                    "entera, deja el saldo en 0 e informa el costo de la entrada."
                ],
            },
        ],
    },
    {
        "number": 4,
        "folder": "4-consultas",
        "title": "Consultas de stock y kardex",
        "purpose": (
            "Los usuarios autorizados consultan el saldo de un producto, el stock de la sucursal, saldos "
            "por lote, el kardex y una operación por su clave; fuera de su empresa reciben `404`."
        ),
        "data": COMMON_DATA,
        "steps": [
            {
                "file": "01-entrada.md",
                "title": "Entrada de arroz y aceite",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": ENTRY_10_ARROZ_5_ACEITE,
                "expect": 201,
                "why": ["Prepara los datos de las consultas."],
            },
            {
                "file": "02-salida.md",
                "title": "Salida de 3 unidades de arroz",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(2, "SALE", SALE_DOC, ln(3, ARROZ, "3")),
                "expect": 201,
                "why": ["Agrega un segundo movimiento al kardex del arroz."],
            },
            {
                "file": "03-saldo-de-un-producto.md",
                "title": "Saldo del arroz en la sucursal",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{BASE}/balances/{ARROZ}",
                "expect": 200,
                "why": ["Un producto sin movimientos respondería saldo `0.0000`, no `404`."],
            },
            {
                "file": "04-stock-de-la-sucursal.md",
                "title": "Stock de la sucursal (solo con existencias)",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{BASE}/balances?in_stock_only=true",
                "expect": 200,
                "why": ["Paginado (`page_size` 20 por defecto, máximo 100) y ordenado por producto."],
            },
            {
                "file": "05-saldos-por-lote.md",
                "title": "Saldos de varios productos en una llamada",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "POST",
                "path": f"{BASE}/balances/lookup",
                "body": {"company_product_ids": [ACEITE, SERVICIO, ARROZ]},
                "expect": 200,
                "why": ["Pensado para que Sales revise todas las líneas de una venta antes de confirmarla."],
            },
            {
                "file": "06-kardex.md",
                "title": "Kardex del arroz",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{BASE}/kardex/{ARROZ}",
                "expect": 200,
                "why": ["Orden cronológico por `balance_sequence`, con saldos anterior y nuevo encadenados."],
            },
            {
                "file": "07-operacion-por-clave.md",
                "title": "Operación por su clave",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{COMPANY}/inventory-operations/by-key/{uid('01', 1)}",
                "expect": 200,
                "why": ["Permite a un consumidor conciliar una operación cuya respuesta perdió."],
            },
            {
                "file": "08-empresa-sin-membresia.md",
                "title": "Consultar una empresa sin membresía",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"/api/v1/companies/{OTHER_COMPANY}/branches/{BRANCH}/balances",
                "expect": 404,
                "why": ["Fuera del alcance del usuario: `404` sin revelar si la empresa existe."],
            },
        ],
    },
]


# ==========================================================================================
# Fase B (013): ajustes, conteos, valoración FIFO y políticas
# ==========================================================================================

ACCION = "accion"
"""Escritura de un usuario humano (ajustes, conteos, políticas): permiso + membresía (+ asignación a
la sucursal en ajustes y conteos); una cuenta de servicio recibe `403` aunque tenga el permiso."""

BRANCH_B = "d44b0000-0000-4000-8000-000000000002"
"""Segunda sucursal ficticia (`ACTIVE`) a la que **ningún** usuario de prueba está asignado."""

COMPANY_BASE = f"/api/v1/companies/{COMPANY}"

DATA_013 = COMMON_DATA + [
    ("Sucursal sin asignar", BRANCH_B, "Sucursal ficticia `ACTIVE` sin usuarios asignados."),
    ("Compra", PURCHASE_DOC, "Documento ficticio de Purchase."),
    ("Venta", SALE_DOC, "Documento ficticio de Sales."),
]


def adjustment(key: int, product: str, kind: str, quantity: str, reason: str, *, unit_cost: str | None = None, branch: str = BRANCH) -> dict:
    return {
        "adjustment_key": uid("05", key),
        "branch_id": branch,
        "company_product_id": product,
        "adjustment_type": kind,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "reason": reason,
    }


EXERCISES += [
    {
        "number": 5,
        "folder": "5-ajustes",
        "title": "Ajustes de inventario",
        "purpose": (
            "Un usuario de la bodega, asignado a la sucursal, corrige el inventario con ajustes que se "
            "aplican al registrarlos: un ajuste negativo valorizado con FIFO, uno positivo con el costo de "
            "la capa más reciente, uno positivo de un producto sin capas (costo obligatorio) y un ajuste en "
            "una sucursal a la que el usuario no está asignado."
        ),
        "data": DATA_013,
        "steps": [
            {
                "file": "01-entrada.md",
                "title": "Entrada de 10 unidades de arroz a 2 500,50",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10", "2500.50")),
                "expect": 201,
                "why": ["Crea el saldo y una capa FIFO de 10 a 2 500,50."],
            },
            {
                "file": "02-ajuste-negativo.md",
                "title": "Ajuste negativo de 3 unidades dañadas",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-adjustments",
                "body": adjustment(1, ARROZ, "NEGATIVE", "3", "Producto dañado en bodega"),
                "expect": 201,
                "save": {"AJUSTE": "id"},
                "why": [
                    "Se aplica en el acto (sin aprobación) como un movimiento `NEGATIVE_ADJUSTMENT` del kardex.",
                    "El costo sale de las capas FIFO (no se informa `unit_cost`); el motivo es obligatorio.",
                    "El usuario operativo no viaja en el cuerpo: lo informa Operational Context para el usuario del token.",
                ],
            },
            {
                "file": "03-ajuste-positivo.md",
                "title": "Ajuste positivo con el costo de la capa más reciente",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-adjustments",
                "body": adjustment(2, ARROZ, "POSITIVE", "2", "Sobrante encontrado en estantería"),
                "expect": 201,
                "why": ["Sin `unit_cost`: la nueva capa toma el costo de la capa más reciente del producto (2 500,50)."],
            },
            {
                "file": "04-ajuste-positivo-sin-capas.md",
                "title": "Ajuste positivo de un producto sin capas, sin costo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-adjustments",
                "body": adjustment(3, ACEITE, "POSITIVE", "4", "Inventario inicial encontrado"),
                "expect": 422,
                "why": [
                    "El aceite nunca tuvo capas en la sucursal: no hay costo conocido y `unit_cost` es obligatorio "
                    "(`UNIT_COST_REQUIRED`). Ninguna cantidad entra sin costo."
                ],
            },
            {
                "file": "05-ajuste-positivo-con-costo.md",
                "title": "El mismo ajuste con su costo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-adjustments",
                "body": adjustment(4, ACEITE, "POSITIVE", "4", "Inventario inicial encontrado", unit_cost="9800"),
                "expect": 201,
                "why": ["Con `unit_cost` la capa se crea con ese costo."],
            },
            {
                "file": "06-sucursal-no-asignada.md",
                "title": "Ajuste en una sucursal no asignada",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-adjustments",
                "body": adjustment(5, ARROZ, "POSITIVE", "1", "Prueba de asignación", unit_cost="1", branch=BRANCH_B),
                "expect": 403,
                "why": [
                    "El usuario es miembro de la empresa pero no está asignado a esa sucursal: "
                    "`BRANCH_ACCESS_DENIED`. Las consultas no exigen asignación; los ajustes y conteos sí."
                ],
            },
            {
                "file": "07-consultar-el-ajuste.md",
                "title": "Consultar el ajuste con su movimiento",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{COMPANY_BASE}/inventory-adjustments/<AJUSTE>",
                "expect": 200,
                "why": ["El ajuste es inmutable: se corrige con otro ajuste de sentido contrario."],
            },
        ],
    },
    {
        "number": 6,
        "folder": "6-conteos",
        "title": "Conteos físicos",
        "purpose": (
            "Un conteo completo con faltante y sobrante que se aplica como una sola operación de ajustes, "
            "un conteo cuya finalización dejaría un saldo negativo (no aplica nada) y su cancelación."
        ),
        "data": DATA_013,
        "steps": [
            {
                "file": "01-entrada.md",
                "title": "Entrada de arroz y aceite",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": ENTRY_10_ARROZ_5_ACEITE,
                "expect": 201,
                "why": ["Saldo de 10 arroces y 5,5 aceites, cada uno con su capa de costo."],
            },
            {
                "file": "02-crear-conteo.md",
                "title": "Crear el conteo de la sucursal",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts",
                "body": {"branch_id": BRANCH, "observations": "Conteo mensual ficticio"},
                "expect": 201,
                "save": {"CONTEO": "id"},
                "why": ["Nace en `DRAFT` con `version` 1; el responsable es el usuario operativo del token."],
            },
            {
                "file": "03-iniciar.md",
                "title": "Iniciar el conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO>/start",
                "body": {"version": 1},
                "expect": 200,
                "why": ["Pasa a `IN_PROGRESS` (`version` 2). Solo un conteo en curso por sucursal."],
            },
            {
                "file": "04-contar-arroz.md",
                "title": "Registrar 8 arroces contados",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO>/details/{ARROZ}",
                "body": {"counted_quantity": "8"},
                "expect": 200,
                "why": ["Se guarda el saldo del sistema en ese momento (10) y la diferencia (−2)."],
            },
            {
                "file": "05-contar-aceite.md",
                "title": "Registrar 6 aceites contados",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO>/details/{ACEITE}",
                "body": {"counted_quantity": "6"},
                "expect": 200,
                "why": ["Diferencia +0,5: un sobrante que tomará el costo de la capa más reciente del aceite."],
            },
            {
                "file": "06-completar.md",
                "title": "Completar el conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO>/complete",
                "body": {"completion_key": uid("06", 1), "version": 2},
                "expect": 200,
                "why": [
                    "Una sola operación `ADJUSTMENT` (origen `COUNT`) con una línea por diferencia distinta de 0, "
                    "todo o nada; un ajuste por línea enlazado a su detalle.",
                    "La misma `completion_key` repetida devuelve el mismo resultado.",
                ],
            },
            {
                "file": "07-consultar.md",
                "title": "Consultar el conteo completado",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO>",
                "expect": 200,
                "why": ["Incluye los detalles y, por estar completado, sus ajustes."],
            },
            {
                "file": "08-segundo-conteo.md",
                "title": "Crear un segundo conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts",
                "body": {"branch_id": BRANCH},
                "expect": 201,
                "save": {"CONTEO_2": "id"},
                "why": ["El conteo anterior ya terminó: se puede iniciar otro en la sucursal."],
            },
            {
                "file": "09-iniciar-segundo.md",
                "title": "Iniciar el segundo conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO_2>/start",
                "body": {"version": 1},
                "expect": 200,
                "why": ["`IN_PROGRESS` con `version` 2."],
            },
            {
                "file": "10-contar-arroz-cero.md",
                "title": "Registrar 0 arroces contados",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO_2>/details/{ARROZ}",
                "body": {"counted_quantity": "0"},
                "expect": 200,
                "why": ["Diferencia −8 sobre el saldo de ese momento."],
            },
            {
                "file": "11-venta-intermedia.md",
                "title": "Una venta de 5 arroces antes de completar",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(2, "SALE", SALE_DOC, ln(5, ARROZ, "5")),
                "expect": 201,
                "why": ["El saldo vigente baja a 3."],
            },
            {
                "file": "12-completar-con-saldo-insuficiente.md",
                "title": "Completar el segundo conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO_2>/complete",
                "body": {"completion_key": uid("06", 2), "version": 2},
                "expect": 409,
                "why": [
                    "La diferencia registrada (−8) se aplica sobre el saldo vigente (3): quedaría negativo. Se "
                    "rechaza con `INSUFFICIENT_STOCK` y `shortages`; no se aplica nada y el conteo sigue en curso."
                ],
            },
            {
                "file": "13-cancelar.md",
                "title": "Cancelar el segundo conteo",
                "actor": "inventario.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-counts/<CONTEO_2>/cancel",
                "body": {"reason": "Conteo repetido por la venta intermedia", "version": 2},
                "expect": 200,
                "why": ["Queda `CANCELLED` sin ajustes; sus detalles ya no se pueden modificar."],
            },
        ],
    },
    {
        "number": 7,
        "folder": "7-valoracion",
        "title": "Valoración FIFO",
        "purpose": (
            "Dos entradas con costos distintos, una salida que consume dos capas, el valor de la sucursal, "
            "las capas y los consumos de la salida, y los reversos con valoración: una entrada cuya capa ya "
            "se consumió no se revierte hasta revertir la venta."
        ),
        "data": DATA_013,
        "steps": [
            {
                "file": "01-entrada-a-1000.md",
                "title": "Entrada de 10 arroces a 1 000",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10", "1000")),
                "expect": 201,
                "save": {"OP_ENTRADA": "id"},
                "why": ["Primera capa: 10 a 1 000."],
            },
            {
                "file": "02-entrada-a-1300.md",
                "title": "Entrada de 5 arroces a 1 300",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries",
                "body": operation(2, "PURCHASE", PURCHASE_DOC, ln(2, ARROZ, "5", "1300")),
                "expect": 201,
                "why": ["Segunda capa: 5 a 1 300. Valor del saldo: 16 500."],
            },
            {
                "file": "03-salida-de-12.md",
                "title": "Salida de 12 arroces",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs",
                "body": operation(3, "SALE", SALE_DOC, ln(3, ARROZ, "12")),
                "expect": 201,
                "save": {"OP_SALIDA": "id", "MOV_SALIDA": "movements[0].id"},
                "why": [
                    "Consume 10 a 1 000 y 2 a 1 300: `movement_value` 12 600 y `unit_cost` 1 050 (informativo).",
                    "Sales guarda este costo; no lo calcula. `cost_known = true`: ninguna unidad sin costo histórico.",
                ],
            },
            {
                "file": "04-valor-de-la-sucursal.md",
                "title": "Valor del inventario de la sucursal",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{BASE}/valuation",
                "expect": 200,
                "why": ["Quedan 3 a 1 300: 3 900. El valor se recalcula siempre desde las capas abiertas."],
            },
            {
                "file": "05-capas.md",
                "title": "Capas del arroz, incluidas las cerradas",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{BASE}/valuation/{ARROZ}/layers?include_closed=true",
                "expect": 200,
                "why": ["En orden FIFO; la primera quedó cerrada (`remaining_quantity` 0)."],
            },
            {
                "file": "06-consumos-de-la-salida.md",
                "title": "Consumos que explican el costo de la salida",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{COMPANY_BASE}/inventory-movements/<MOV_SALIDA>/cost-consumptions",
                "expect": 200,
                "why": ["Un consumo `CONSUME` por capa tomada; la suma de `cost_amount` es el `movement_value`."],
            },
            {
                "file": "07-reverso-de-entrada-consumida.md",
                "title": "Revertir la primera entrada después de la venta",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
                "body": reversal(4, "Anulación de la compra ficticia"),
                "expect": 409,
                "why": ["Su capa ya entregó unidades a la venta: `ENTRY_LAYER_CONSUMED`, sin cambios."],
            },
            {
                "file": "08-reverso-de-la-salida.md",
                "title": "Revertir la venta",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-outputs/<OP_SALIDA>/reversal",
                "body": reversal(5, "Anulación de la venta ficticia"),
                "expect": 201,
                "why": [
                    "Devuelve cada cantidad a la misma capa con el mismo costo (consumos `RESTORE`); el valor vuelve a 16 500.",
                    "Una salida aplicada antes de la valoración (sin consumos FIFO) no se puede revertir: "
                    "`409 OUTPUT_NOT_VALUED`; se corrige con un ajuste positivo con costo.",
                ],
            },
            {
                "file": "09-reverso-de-entrada-intacta.md",
                "title": "Revertir ahora la primera entrada",
                "actor": "operador",
                "kind": OPERACION,
                "method": "POST",
                "path": "/api/v1/inventory-entries/<OP_ENTRADA>/reversal",
                "body": reversal(6, "Anulación de la compra ficticia"),
                "expect": 201,
                "why": ["Su capa volvió a estar completa: se retira entera (`ENTRY_REVERSAL`) con su costo de 1 000."],
            },
        ],
    },
    {
        "number": 8,
        "folder": "8-politicas",
        "title": "Políticas de inventario",
        "purpose": (
            "El administrador consulta la política por defecto, registra la de la empresa (solo FIFO), la "
            "cambia con control de versión y configura los niveles de reposición de un producto en la "
            "sucursal (una política activa por producto y sucursal)."
        ),
        "data": DATA_013,
        "steps": [
            {
                "file": "01-politica-por-defecto.md",
                "title": "Consultar la política sin registrarla",
                "actor": "admin.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{COMPANY_BASE}/inventory-policy",
                "expect": 200,
                "why": ["Se informa la política por defecto (`PERPETUAL`, `FIFO`, `STANDARD`) con `registered: false`."],
            },
            {
                "file": "02-registrar-politica.md",
                "title": "Registrar la política de la empresa",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-policy",
                "body": {"inventory_system": "PERPETUAL", "valuation_method": "FIFO", "replenishment_strategy": "STANDARD"},
                "expect": 201,
                "why": ["Una política por empresa; `is_active` es solo de lectura (no hay desactivación)."],
            },
            {
                "file": "03-cambiar-a-jit.md",
                "title": "Cambiar la estrategia de reposición",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{COMPANY_BASE}/inventory-policy",
                "body": {"inventory_system": "PERPETUAL", "valuation_method": "FIFO", "replenishment_strategy": "JIT", "version": 1},
                "expect": 200,
                "why": ["Exige la `version` vigente; una versión vieja responde `409 VERSION_CONFLICT`."],
            },
            {
                "file": "04-otro-metodo-de-valoracion.md",
                "title": "Pedir promedio ponderado",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "PUT",
                "path": f"{COMPANY_BASE}/inventory-policy",
                "body": {
                    "inventory_system": "PERPETUAL",
                    "valuation_method": "WEIGHTED_AVERAGE",
                    "replenishment_strategy": "JIT",
                    "version": 2,
                },
                "expect": 422,
                "why": ["Esta fase solo valora con FIFO: `VALUATION_METHOD_NOT_SUPPORTED`."],
            },
            {
                "file": "05-politica-de-producto.md",
                "title": "Niveles de reposición del arroz en la sucursal",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-policies",
                "body": {
                    "branch_id": BRANCH,
                    "company_product_id": ARROZ,
                    "minimum_stock": "5",
                    "target_stock": "20",
                    "service_level": "0.95",
                    "safety_stock_method": "BASIC",
                    "calculation_window_days": 90,
                    "replenishment_mode": "MANUAL",
                    "auto_purchase_enabled": False,
                },
                "expect": 201,
                "save": {"POLITICA": "id"},
                "why": ["Solo configuración: no genera compras ni movimientos."],
            },
            {
                "file": "06-politica-duplicada.md",
                "title": "Otra política activa para el mismo producto",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-policies",
                "body": {
                    "branch_id": BRANCH,
                    "company_product_id": ARROZ,
                    "minimum_stock": "1",
                    "safety_stock_method": "BASIC",
                    "replenishment_mode": "MANUAL",
                },
                "expect": 409,
                "why": ["Una sola política activa por producto y sucursal: `ACTIVE_POLICY_EXISTS`."],
            },
            {
                "file": "07-inactivar.md",
                "title": "Inactivar la política del arroz",
                "actor": "admin.test",
                "kind": ACCION,
                "method": "POST",
                "path": f"{COMPANY_BASE}/inventory-policies/<POLITICA>/deactivate",
                "body": {"version": 1},
                "expect": 200,
                "why": ["No se elimina: queda inactiva y se puede crear otra."],
            },
            {
                "file": "08-consultar-politicas.md",
                "title": "Consultar las políticas de la sucursal",
                "actor": "inventario.test",
                "kind": CONSULTA,
                "method": "GET",
                "path": f"{COMPANY_BASE}/inventory-policies?branch_id={BRANCH}",
                "expect": 200,
                "why": ["La bodega consulta las políticas pero no las configura (solo administradores y supervisores)."],
            },
        ],
    },
]
