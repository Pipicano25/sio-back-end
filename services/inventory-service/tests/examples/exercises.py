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
                    "`unit_cost` es opcional y solo se guarda; esta fase no valora el inventario.",
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
                "body": operation(2, "PURCHASE", PURCHASE_DOC, ln(3, SERVICIO, "1")),
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
                "body": operation(1, "PURCHASE", PURCHASE_DOC, ln(1, ARROZ, "10")),
                "expect": 201,
                "why": ["Prepara el saldo de la sucursal para las salidas."],
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
            "`company_id` obligatorio: reverso de una entrada sin saldo suficiente, reverso de una salida, "
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
                "why": ["Revertir 10 dejaría el saldo en -4: se rechaza con `INSUFFICIENT_STOCK` sin cambios."],
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
                "why": ["Con el saldo de nuevo en 10, el reverso deja el saldo en 0 y copia el `unit_cost` original."],
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
