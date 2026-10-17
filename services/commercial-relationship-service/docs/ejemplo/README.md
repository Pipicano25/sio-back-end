# Ejercicios de uso — Commercial Relationship Service

Ejercicios paso a paso, ejecutados automáticamente contra la API por `tests/examples/test_examples.py`
(Principio XXII). Muestran cómo **adoptar productos**, **incorporar clientes**, **seleccionar y bloquear
proveedores** (Fase A) y cómo configurar **presentaciones**, **proveedores por producto**, **condiciones de
pago** y **listas de precios** (Fase B), y qué usuario de prueba puede hacer cada llamada.

| Ejercicio | Qué enseña | Datos |
| --- | --- | --- |
| [1 — Adopción de productos](1-adopcion-de-productos/ORDEN.md) | Adoptar productos globales con los datos privados de la empresa; rechazos (inactivo, incompleto, adopción y código repetidos); precio y moneda con sus decimales; consulta por lotes; inactivar y reactivar; resumen de mis empresas, una por página | **Reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) |
| [2 — Clientes](2-clientes/ORDEN.md) | Cliente persona y cliente organización con contacto preferido; contacto de otra organización; la propia empresa como cliente; modificar, inactivar y reactivar | Ficticios |
| [3 — Proveedores](3-proveedores/ORDEN.md) | Seleccionar proveedores; la misma organización como cliente y proveedor; bloquear con motivo; editar sin desbloquear; desbloquear e inactivar | Ficticios |
| [4 — Presentaciones](4-presentaciones/ORDEN.md) | Adoptar presentaciones globales; predeterminada de compra y su cambio en la misma operación; presentación de otro producto y adopción repetida (rechazos); inactivar la predeterminada | Producto **real** (fila 40); presentaciones ficticias |
| [5 — Proveedores por producto y condiciones](5-proveedores-por-producto-y-condiciones/ORDEN.md) | Relación general y por presentación; unidad distinta de la base y relación repetida (rechazos); contado con plazo (rechazo), contado con descuento y crédito predeterminado | Producto y `Nombre Proveedor` **reales** (fila 40); proveedor, costos y condiciones ficticios |
| [6 — Listas de precios](6-listas-de-precios/ORDEN.md) | Lista predeterminada; precio real; solapamiento y precio en vigencia (rechazos); cambio de precio con vigencia futura; precio aplicable por presentación y presentación sin precio (sin respaldo, spec 019) | `Precio Lista 10` **real** (fila 16577); el resto ficticio |
| [7 — Políticas de precios](7-politicas-de-precios/ORDEN.md) | Políticas de ganancia de una lista (spec 021): presentación en dos políticas de la misma lista (rechazo), cambio de porcentaje con historial, retirar una presentación e inactivar una política; nada de esto cambia precios | Productos **reales** (filas 40 y 16577); porcentajes ficticios |
| [8 — Impuesto de compra](8-impuesto-de-compra/ORDEN.md) | Tasa de impuesto de compra del producto (spec 021): sin configurar ≠ 0 %, configuración individual y en lote (todo o nada) | Productos **reales** (filas 40 y 16577); tasas ficticias |
| [9 — Actualizaciones automáticas](9-actualizaciones-automaticas/ORDEN.md) | Precio automático desde la recepción física (spec 021): costo real y porcentaje de la política, consulta de las actualizaciones (solo administradores y supervisores) y resolución administrativa de una fallida | Producto **real** (fila 40); recepciones y costos ficticios, falla simulada |
| [10 — Búsqueda progresiva](10-busqueda-progresiva/ORDEN.md) | Buscar por nombre, código y SKU de presentación sin repetir productos; continuar desde la posición del último producto sin conteos; evaluar filtros sobre un lote de ids; presentaciones de varios productos en una llamada; límites (rechazos) (spec 022) | Productos **reales** (filas 40, 413 y 16577); presentaciones y SKU ficticios |

- [Usuarios y permisos](usuarios-y-permisos.md): cómo se evalúan los permisos y la membresía, los usuarios
  de prueba y la matriz de todas las URL.
- [Mapeo de columnas del Excel](mapeo-campos-excel.md): qué columna de la fuente va a `CompanyProduct`, a
  `SupplierProduct` y a las listas de precios, y cuáles pertenecen a otros servicios.

Cada ejercicio es independiente: puede ejecutarse en una base nueva.

## Antes de empezar

1. **Servicios en ejecución.** Commercial Relationship en `http://localhost:8005` (entorno del servicio) o
   `http://localhost:8106` (entorno integrado), con Keycloak, Operational Context, Product Catalog, Party
   Identity y, para el ejercicio 5, Payment Reference disponibles.
2. **Datos en los otros servicios.** Las llamadas marcadas **«Otro servicio»** no van a Commercial
   Relationship: obtienen `id` de Operational Context (empresa), Product Catalog (productos y presentaciones
   globales, unidad base), Party Identity (personas, organizaciones y contactos) o Payment Reference (tipos de
   condición de pago). En la validación automática esos resultados se simulan con `id` ficticios. **Ningún
   usuario necesita permisos de Payment Reference** para registrar condiciones: el servicio lo consulta con su
   propia identidad técnica (DS-02).
3. **Membresía en la empresa.** El usuario que ejecuta el ejercicio debe tener una membresía `ACTIVE` en la
   empresa en Operational Context. Sin ella, todas las URL de este servicio responden `404`, **también para
   `admin.test`**: ningún permiso de usuario exime de la membresía (DS-03). El resumen de empresas
   (`GET /api/v1/company-summaries`) no responde `404`: solo lista las empresas donde el usuario es miembro.
4. **Token.** La contraseña de todos los usuarios de prueba está en la variable
   `KEYCLOAK_TEST_USER_PASSWORD` (`infrastructure/.env`). Cómo pedir el token:
   [usuarios-y-permisos.md](usuarios-y-permisos.md#cómo-obtener-el-token-de-cada-usuario).

## Cómo leer los ejercicios

- `ORDEN.md` de cada ejercicio: orden de los pasos, por qué y qué `id` se guardan.
- `00-datos-…md`: los datos de origen y cómo se interpretan.
- Un archivo por paso: método y URL, JSON, permiso que exige la URL (con los usuarios que pueden y los que
  no), por qué se hace así y la respuesta esperada (abreviada).
- `USUARIOS.md`: resumen por usuario, permiso por URL y ejemplos con usuarios que pueden y que no.
- Las variables `<NOMBRE>` se reemplazan por los `id` guardados en pasos anteriores.
- Los importes (`unit_price`, `credit_limit`, costos, cantidades y porcentajes)
  se envían como número o texto y se **devuelven siempre como texto decimal** (por ejemplo `"1500.00"`), nunca
  como número JSON. `unit_price` y `credit_limit` usan los decimales de su moneda.

## Validación

Los documentos de las carpetas numeradas y `usuarios-y-permisos.md` se **generan** desde los ejercicios de
`tests/examples/` y la prueba falla si no coinciden con lo que responde la API. Después de cambiar un
ejercicio, un contrato o el realm:

```bash
COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples
```

Este `README.md` y `mapeo-campos-excel.md` se escriben a mano.
