# Ejercicios de uso de inventory-service

Ejercicios paso a paso, ejecutables y validados automáticamente por
`tests/examples/test_examples.py` (Constitución, Principio XXII). Todo lo que hay en estas carpetas,
salvo este archivo, lo genera esa prueba: si cambia un ejercicio, un contrato o la plantilla del
realm, se regenera con `INVENTORY_EXAMPLES_WRITE=1 pytest tests/examples`.

| Ejercicio | Qué muestra |
| --- | --- |
| [1-entradas-de-compra](1-entradas-de-compra/ORDEN.md) | Entrada de varias líneas con costo, repetición idempotente, clave reutilizada con otro contenido y producto sin control de inventario |
| [2-salidas-de-venta](2-salidas-de-venta/ORDEN.md) | Salida con saldo suficiente, rechazo completo por saldo insuficiente y salida con costo |
| [3-reversos](3-reversos/ORDEN.md) | Reverso de una entrada cuya capa ya se consumió, reverso de salida, reverso repetido y reverso pedido desde otra empresa |
| [4-consultas](4-consultas/ORDEN.md) | Saldo de un producto, stock de la sucursal, saldos por lote, kardex, operación por clave y empresa sin membresía |
| [5-ajustes](5-ajustes/ORDEN.md) | Ajuste negativo valorizado con FIFO, ajuste positivo con el costo de la capa más reciente, producto sin capas (costo obligatorio) y sucursal no asignada |
| [6-conteos](6-conteos/ORDEN.md) | Conteo con faltante y sobrante aplicado como una operación de ajustes, conteo que dejaría saldo negativo y cancelación |
| [7-valoracion](7-valoracion/ORDEN.md) | Capas FIFO, salida que consume dos capas, valor de la sucursal, consumos, reverso de una entrada consumida y reverso de la venta |
| [8-politicas](8-politicas/ORDEN.md) | Política por defecto, registro y cambio de la política de la empresa (solo FIFO) y niveles de reposición por producto |

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
- Ajustes y conteos (013): el usuario debe estar asignado a la sucursal en Operational Context; las
  políticas solo las configuran `admin.test` y `supervisor.test`.

## Convenciones

- Datos **ficticios**: no existe una fuente del sistema anterior para movimientos de inventario.
- Cantidades y costos en unidad base, como cadena decimal; las respuestas llevan 4 decimales y los
  valores monetarios (`movement_value`, `inventory_value`) 2.
- `<VARIABLE>`: valor guardado de la respuesta de un paso anterior (ver `ORDEN.md`).
- `<asignado por Inventory>`: valor que Inventory genera en cada ejecución (`id` de operaciones y
  movimientos, momentos, `trace_id`).
- Cada archivo de paso indica el método y la URL, el JSON de la solicitud, el permiso, qué usuarios
  pueden y cuáles no (y por qué), la justificación de cada decisión y la respuesta esperada.
