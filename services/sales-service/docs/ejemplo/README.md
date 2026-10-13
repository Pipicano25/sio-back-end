# Ejemplos de uso de sales-service

Ejercicios **validados automáticamente** (Principio XXII) sobre la API de ventas. Todos los datos son
**ficticios** y sus identificadores son fijos; ningún dato legal real.

Cada carpeta es un ejercicio independiente con:

- `ORDEN.md`: los pasos en orden, por qué ese orden y las variables que se pasan entre pasos.
- `00-datos-ficticios.md`: los datos que se suponen existentes en las dependencias.
- Un archivo por paso: la llamada, la solicitud, por qué, el permiso exigido, qué usuarios pueden
  ejecutarla y la respuesta esperada.
- `USUARIOS.md`: la respuesta de cada usuario de prueba en cada paso.

`usuarios-y-permisos.md` resume los permisos de la API, los usuarios de prueba del realm y cómo obtener
sus tokens (la contraseña se toma de la variable `KEYCLOAK_TEST_USER_PASSWORD`; nunca aparece en estos
documentos).

| Ejercicio | Qué muestra |
| --- | --- |
| [1-secuencias](1-secuencias/ORDEN.md) | Secuencia mensual, consulta y rechazo de una segunda activa |
| [2-borrador-y-precios](2-borrador-y-precios/ORDEN.md) | Borrador con precio de lista pedida y de lista predeterminada, siempre por presentación; sin precio manual; lista inexistente, lista sin precio y producto sin control de inventario |
| [3-disponibilidad](3-disponibilidad/ORDEN.md) | Existencias por producto en unidad base, sin reservar |
| [4-confirmacion](4-confirmacion/ORDEN.md) | Precio cambiado (`409 PRICES_CHANGED`), Inventory caído, reintento idempotente |
| [5-existencias-insuficientes](5-existencias-insuficientes/ORDEN.md) | La venta se confirma completa o no se confirma |
| [6-rentabilidad](6-rentabilidad/ORDEN.md) | Costo FIFO y margen solo con `read-profitability`; costo desconocido |
| [7-anulacion](7-anulacion/ORDEN.md) | Anulación de borrador y de venta confirmada con reverso exacto |
| [8-consultas](8-consultas/ORDEN.md) | Listado filtrado y aislamiento entre empresas |

**No obvio**:

- El precio siempre lo resuelve Commercial Relationship; no se acepta precio manual, fecha de negocio ni
  condición de pago (el MVP solo vende de contado y la fecha es la del día en que se confirma).
- Costo y margen solo se ven con `perm:sales:sales:read-profitability`; `perm:sales:all:read` no lo incluye
  y el grupo `ventas` no lo tiene.
- Escribir exige además la asignación a la sucursal de la venta; ningún token técnico escribe ventas.

La documentación por ejercicio y `usuarios-y-permisos.md` se generan con
`SALES_EXAMPLES_WRITE=1 pytest tests/examples` y la prueba `tests/examples/test_examples.py` falla si quedan
desactualizadas respecto de la API o de la plantilla del realm.
