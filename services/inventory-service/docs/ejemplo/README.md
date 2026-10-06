# Ejercicios de uso de inventory-service

Ejercicios paso a paso, ejecutables y validados automáticamente por
`tests/examples/test_examples.py` (Constitución, Principio XXII). Todo lo que hay en estas carpetas,
salvo este archivo, lo genera esa prueba: si cambia un ejercicio, un contrato o la plantilla del
realm, se regenera con `INVENTORY_EXAMPLES_WRITE=1 pytest tests/examples`.

| Ejercicio | Qué muestra |
| --- | --- |
| [1-entradas-de-compra](1-entradas-de-compra/ORDEN.md) | Entrada de varias líneas con costo, repetición idempotente, clave reutilizada con otro contenido y producto sin control de inventario |
| [2-salidas-de-venta](2-salidas-de-venta/ORDEN.md) | Salida con saldo suficiente, rechazo completo por saldo insuficiente y salida con costo |
| [3-reversos](3-reversos/ORDEN.md) | Reverso de entrada sin saldo, reverso de salida, reverso repetido y reverso pedido desde otra empresa |
| [4-consultas](4-consultas/ORDEN.md) | Saldo de un producto, stock de la sucursal, saldos por lote, kardex, operación por clave y empresa sin membresía |

Permisos, usuarios y cómo obtener los tokens: [usuarios-y-permisos.md](usuarios-y-permisos.md).

## Requisitos para ejecutarlos a mano

- Entorno integrado levantado: Keycloak (reconstruido desde la plantilla del realm), Operational
  Context, Commercial Relationship e inventory-service (`http://localhost:8109`).
- La empresa, la sucursal, el usuario operativo y los productos de `00-datos-ficticios.md` deben
  existir en Operational Context y Commercial Relationship; en el entorno integrado se usan sus
  propios identificadores en lugar de los de los ejercicios.
- Token del usuario de prueba con la contraseña de la variable `KEYCLOAK_TEST_USER_PASSWORD`, o de la
  cuenta de servicio `inventory-test-operator` con el secreto de
  `INVENTORY_TEST_OPERATOR_CLIENT_SECRET`. Nunca se escriben contraseñas ni tokens en estos documentos.
- Purchase y Sales todavía no existen: las operaciones las aplica la cuenta de servicio de pruebas.

## Convenciones

- Datos **ficticios**: no existe una fuente del sistema anterior para movimientos de inventario.
- Cantidades en unidad base, como cadena decimal; las respuestas siempre llevan 4 decimales.
- `<VARIABLE>`: valor guardado de la respuesta de un paso anterior (ver `ORDEN.md`).
- `<asignado por Inventory>`: valor que Inventory genera en cada ejecución (`id` de operaciones y
  movimientos, momentos, `trace_id`).
- Cada archivo de paso indica el método y la URL, el JSON de la solicitud, el permiso, qué usuarios
  pueden y cuáles no (y por qué), la justificación de cada decisión y la respuesta esperada.
