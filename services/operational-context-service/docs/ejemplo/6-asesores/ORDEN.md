# Ejercicio 6 — Asesores de la empresa

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar el **asesor principal**, rechazar un segundo principal, agregar un asesor no principal, **cambiar el asesor principal** en una sola operación y consultar el **historial**.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<ORG_EMPRESA>` y las tres personas. | 4 | — |
| 02 | [02-registrar-empresa.md](02-registrar-empresa.md) | Crear la empresa asesorada. | 1 | 01 |
| 03 | [03-registrar-asesores.md](03-registrar-asesores.md) | Registrar el asesor principal y uno no principal. | 3 | 01, 02 |
| 04 | [04-cambiar-asesor-principal.md](04-cambiar-asesor-principal.md) | Reemplazar al asesor 1 por el asesor 2 en una sola operación. | 1 | 01, 02, 03 |
| 05 | [05-historial-y-cierre.md](05-historial-y-cierre.md) | Ver el historial completo y cerrar al asesor no principal. | 3 | 02, 03 |

## Por qué este orden

1. **Principal antes del cambio.** Sin asesor principal vigente, el cambio responde `409 NO_ACTIVE_PRIMARY_ADVISOR`.
2. **Cerrar no reabre.** Una asignación cerrada es inmutable: el historial solo crece.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<ORG_EMPRESA>` | 01 | 02 |
| `<PERSONA_ASESOR_1>` | 01 | 03 |
| `<PERSONA_ASESOR_2>` | 01 | 03, 04 |
| `<PERSONA_ASESOR_3>` | 01 | 03 |
| `<EMPRESA>` | 02 | 03, 04, 05 |
| `<ASESORIA_1>` | 03 | 04 |
| `<ASESORIA_3>` | 03 | 05 |
| `<ASESORIA_2>` | 04 | — |

[Empezar → paso 01](01-consultar-datos.md)
