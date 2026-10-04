# Ejercicio 2 — Clientes persona y organización

[← Todos los ejercicios](../README.md)

**Qué enseña:** Incorporar un **cliente persona** y un **cliente organización con persona de contacto preferida**, ver los rechazos de un contacto de otra organización y de la **propia empresa como cliente**, modificar el cliente y **inactivarlo y reactivarlo**.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-identidades.md](01-consultar-identidades.md) | Obtener `<EMPRESA>`, la persona, las organizaciones y los contactos. | 7 | — |
| 02 | [02-cliente-persona.md](02-cliente-persona.md) | Registrar a la persona como cliente. | 2 | 01 |
| 03 | [03-cliente-organizacion.md](03-cliente-organizacion.md) | Registrar la organización con su contacto y ver los rechazos. | 3 | 01 |
| 04 | [04-modificar-y-estados.md](04-modificar-y-estados.md) | Cambiar el nombre visible y el ciclo de vida del cliente. | 4 | 01, 02, 03 |

## Por qué este orden

1. **Identidades primero.** El cliente referencia identidades que ya existen en Party Identity.
2. **Alta antes de cambios.** La modificación y los estados se aplican sobre un cliente existente.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 03, 04 |
| `<ORG_EMPRESA>` | 01 | 03 |
| `<PERSONA>` | 01 | 02 |
| `<ORG_CLIENTE>` | 01 | 03 |
| `<CONTACTO>` | 01 | 02, 03 |
| `<ORG_OTRA>` | 01 | — |
| `<CONTACTO_OTRA>` | 01 | 03 |
| `<CLIENTE_PERSONA>` | 02 | 04 |
| `<CLIENTE_ORG>` | 03 | 04 |

[Empezar → paso 01](01-consultar-identidades.md)
