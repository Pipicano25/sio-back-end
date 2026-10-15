# Recorrido del MVP de SIO — guía de validación

Recorrido completo del MVP con los servicios reales: configuración de la empresa → relación comercial y
precios → compras e inventario → ventas con precio por presentación → anulaciones → auditoría →
seguridad entre empresas. Cada paso indica el usuario de prueba, el permiso que exige la URL, la petición y
la respuesta esperada (Principio XXII, feature 017).

**Esta guía se genera desde los pasos de la suite** (`validation/mvp-e2e/scenario/`) y la etapa `guia` de
`bash validation/mvp-e2e/run.sh` exige que sea idéntica a la generada y que cada paso se haya ejecutado contra
los servicios: si una API, un permiso o un valor cambian, la validación falla hasta regenerarla con
`SIO_MVP_GUIDE_WRITE=1 bash validation/mvp-e2e/run.sh --etapa recorrido --etapa seguridad --etapa guia`.

## Datos

**Todos los datos son ficticios**: organizaciones, personas, productos, precios y documentos llevan
"(dato ficticio)" y el identificador de la corrida (`<RUN_ID>`). Los números de identificación se generan con
el patrón de la regla vigente de Party Identity y no corresponden a personas ni empresas reales. Montos sin
impuestos para que costos y márgenes sean exactos (`specs/017-mvp-integral-validation/data-model.md` §3).

## Antes de empezar

1. Entorno integrado levantado (`infrastructure/`), con migraciones y seeds; puertos en `docs/port-map.md`.
2. Token de Keycloak (`http://127.0.0.1:8081`, realm `sio`, cliente `sio-web`); la contraseña de los usuarios
   de prueba es la variable `KEYCLOAK_TEST_USER_PASSWORD` de `infrastructure/.env` (ver
   [usuarios-y-permisos.md](usuarios-y-permisos.md)).

## Convenciones

- `<NOMBRE>` es un valor guardado en un paso anterior (por ejemplo `<EMPRESA_A>` o `<COMPRA_1>`).
- Las URL incluyen el servicio y su puerto; las rutas funcionales llevan `/api/v1` salvo Geography y Payment Reference.
- Errores en RFC 9457 con `code` (`<SERVICIO>.<CAUSA>`).

## Ejercicios

| Ejercicio | Llamadas |
| --- | --- |
| [1 — Configuración de la empresa: organizaciones, personas, empresas, sucursales y usuarios operativos](1-configuracion/ORDEN.md) | 36 |
| [2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas](2-relacion-comercial-y-precios/ORDEN.md) | 24 |
| [3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas](3-compras-e-inventario/ORDEN.md) | 18 |
| [4 — Ventas con precio por presentación (lista indicada y predeterminada), rechazos, costo FIFO y margen](4-ventas/ORDEN.md) | 31 |
| [5 — Anulaciones y reversos](5-anulaciones/ORDEN.md) | 14 |
| [6 — Auditoría del recorrido](6-auditoria/ORDEN.md) | 3 |
| [7 — Seguridad entre empresas y permisos](7-seguridad/ORDEN.md) | 65 |

Evidencia de la validación: `specs/017-mvp-integral-validation/validation-evidence.md`.
