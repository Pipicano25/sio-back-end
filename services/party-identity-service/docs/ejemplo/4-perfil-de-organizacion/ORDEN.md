# Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar el contacto vigente de un proveedor **confirmado desde una empresa**, ver que una solicitud idéntica no crea versión, **reemplazarlo** (se cierra la versión anterior y se crea otra), consultar el **historial**, los rechazos por **geografía incoherente**, por **usuario sin membresía** y por **dependencia caída**, y **cerrar** el perfil sin reemplazo (y el `409` al repetirlo). Muestra además que `compras.test` lee el contacto y `reportes.test`/`consulta.test` no.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-referencias.md](01-consultar-referencias.md) | Obtener `<PAIS_CO>`, `<DIVISION>`, `<CIUDAD>` y `<EMPRESA>`. | 3 | — |
| 02 | [02-registrar-organizacion.md](02-registrar-organizacion.md) | Crear el proveedor (identidad global). | 1 | 01 |
| 03 | [03-registrar-perfil.md](03-registrar-perfil.md) | Crear la versión vigente; la repetición no cambia nada. | 3 | 01, 02 |
| 04 | [04-reemplazar-y-rechazos.md](04-reemplazar-y-rechazos.md) | Crear una versión nueva y ver los rechazos. | 5 | 01, 02 |
| 05 | [05-cerrar-perfil.md](05-cerrar-perfil.md) | Dejar la organización sin perfil vigente. | 3 | 02 |

## Por qué este orden

1. **Referencias primero.** País, ciudad y empresa son de otros servicios: se consultan para conocer sus `id`.
2. **Organización antes que su perfil.** El perfil se registra sobre una organización `ACTIVE`.
3. **Versión vigente para reemplazar y cerrar.** Cada reemplazo o cierre envía la `version` de la vigente.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02, 03, 04 |
| `<DIVISION>` | 01 | 03, 04 |
| `<CIUDAD>` | 01 | 03, 04 |
| `<EMPRESA>` | 01 | 03, 04 |
| `<ORG_PROVEEDOR>` | 02 | 03, 04, 05 |
| `<PERFIL_1>` | 03 | — |
| `<PERFIL_2>` | 04 | — |

[Empezar → paso 01](01-consultar-referencias.md)
