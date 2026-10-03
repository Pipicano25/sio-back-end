# Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización

[← Todos los ejercicios](../README.md)

**Qué enseña:** Recorrer el **árbol CIIU Rev. 5 A.C.** que carga el `seed` (sección → división → grupo → clase), crear un sector en una **clasificación propia** y ver por qué no se inactiva un sector con hijos activos, asignar dos sectores a una organización, **cambiar el principal** con `set-primary` y **cerrar** una asignación.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-recorrer-arbol-ciiu.md](01-recorrer-arbol-ciiu.md) | Obtener las secciones y bajar hasta una clase. | 6 | — |
| 02 | [02-clasificacion-propia.md](02-clasificacion-propia.md) | Crear un sector con un hijo y ver el rechazo al inactivar el padre. | 6 | 01 |
| 03 | [03-consultar-pais.md](03-consultar-pais.md) | Obtener `<PAIS_CO>`. | 1 | — |
| 04 | [04-asignar-sectores.md](04-asignar-sectores.md) | Registrar la organización, asignar dos sectores y cambiar el principal. | 5 | 01, 03 |
| 05 | [05-cerrar-asignacion.md](05-cerrar-asignacion.md) | Cerrar el sector 0123 y consultar las asignaciones. | 3 | 04 |

## Por qué este orden

1. **Seed antes de asignar.** Los sectores CIIU deben existir; los carga el `seed`, no la API.
2. **Padres antes que hijos.** Un sector nuevo exige padre existente, `ACTIVE` y de la misma clasificación.
3. **Asignar antes de cambiar el principal.** `set-primary` actúa sobre una asignación vigente.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<SECCION_A>` | 01 | 02 |
| `<CLASE_CAFE>` | 01 | 04 |
| `<CLASE_TIENDA>` | 01 | 04 |
| `<SECTOR_X>` | 02 | — |
| `<SECTOR_X1>` | 02 | — |
| `<PAIS_CO>` | 03 | 04 |
| `<ORG_CAFE>` | 04 | 05 |
| `<ASIG_CAFE>` | 04 | 05 |
| `<ASIG_TIENDA>` | 04 | — |

[Empezar → paso 01](01-recorrer-arbol-ciiu.md)
