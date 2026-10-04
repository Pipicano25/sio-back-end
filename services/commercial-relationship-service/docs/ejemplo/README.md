# Ejercicios de uso — Commercial Relationship Service

Ejercicios paso a paso, ejecutados automáticamente contra la API por `tests/examples/test_examples.py`
(Principio XXII). Muestran cómo **adoptar productos**, **incorporar clientes** y **seleccionar y bloquear
proveedores**, y qué usuario de prueba puede hacer cada llamada.

| Ejercicio | Qué enseña | Datos |
| --- | --- | --- |
| [1 — Adopción de productos](1-adopcion-de-productos/ORDEN.md) | Adoptar productos globales con los datos privados de la empresa; rechazos (inactivo, incompleto, adopción y código repetidos); precio y moneda con sus decimales; consulta por lotes; inactivar y reactivar; resumen de mis empresas, una por página | **Reales** del sistema anterior (`docs/CAMPOS PRODUCTOS.xlsx`) |
| [2 — Clientes](2-clientes/ORDEN.md) | Cliente persona y cliente organización con contacto preferido; contacto de otra organización; la propia empresa como cliente; modificar, inactivar y reactivar | Ficticios |
| [3 — Proveedores](3-proveedores/ORDEN.md) | Seleccionar proveedores; la misma organización como cliente y proveedor; bloquear con motivo; editar sin desbloquear; desbloquear e inactivar | Ficticios |

- [Usuarios y permisos](usuarios-y-permisos.md): cómo se evalúan los permisos y la membresía, los usuarios
  de prueba y la matriz de todas las URL.
- [Mapeo de columnas del Excel](mapeo-campos-excel.md): qué columna de la fuente va a `CompanyProduct` y
  cuáles pertenecen a otras fases o servicios.

Cada ejercicio es independiente: puede ejecutarse en una base nueva.

## Antes de empezar

1. **Servicios en ejecución.** Commercial Relationship en `http://localhost:8005` (entorno del servicio) o
   `http://localhost:8106` (entorno integrado), con Keycloak, Operational Context, Product Catalog y Party
   Identity disponibles.
2. **Datos en los otros servicios.** Las llamadas marcadas **«Otro servicio»** no van a Commercial
   Relationship: obtienen `id` de Operational Context (empresa), Product Catalog (productos globales) o Party
   Identity (personas, organizaciones y contactos). En la validación automática esos resultados se simulan con
   `id` ficticios.
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
- Los importes (`sale_price`, `reference_cost`) se envían como número o texto y se **devuelven siempre como
  texto decimal** (por ejemplo `"1500.00"`), nunca como número JSON.

## Validación

Los documentos de las carpetas numeradas y `usuarios-y-permisos.md` se **generan** desde los ejercicios de
`tests/examples/` y la prueba falla si no coinciden con lo que responde la API. Después de cambiar un
ejercicio, un contrato o el realm:

```bash
COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples
```

Este `README.md` y `mapeo-campos-excel.md` se escriben a mano.
