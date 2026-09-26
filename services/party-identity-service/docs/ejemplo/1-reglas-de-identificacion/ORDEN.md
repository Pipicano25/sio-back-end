# Ejercicio 1 — Reglas de identificación: crear, versionar y retirar

[← Todos los ejercicios](../README.md)

**Qué enseña:** Cómo se administra una regla de validación sin cambiar código: consultar las reglas de Colombia que dejó la carga inicial, crear una regla nueva, ver los rechazos (`409` duplicada, `422` patrón inválido), corregir su descripción, **crear una nueva versión** cuando cambia el patrón y **retirarla** sin borrarla.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-pais-y-reglas.md](01-consultar-pais-y-reglas.md) | Obtener `<PAIS_CO>` y ver las reglas `CC` que dejó la carga inicial. | 2 | — |
| 02 | [02-crear-regla.md](02-crear-regla.md) | Crear la regla `PASSPORT` / `PA` y comprobar los rechazos. | 3 | 01 |
| 03 | [03-corregir-descripcion.md](03-corregir-descripcion.md) | Modificar en sitio lo que no cambia la validación. | 2 | 02 |
| 04 | [04-nueva-version.md](04-nueva-version.md) | Cambiar el patrón conservando la regla anterior como histórica. | 2 | 02 |
| 05 | [05-retirar-regla.md](05-retirar-regla.md) | Dejar histórica la versión vigente, sin borrarla. | 2 | 04 |

## Por qué este orden

1. **País primero.** Toda regla lleva el `id` del país, que se obtiene de Geography.
2. **Crear antes de versionar.** Solo una regla activa puede tener una nueva versión.
3. **Versión antes de retirar.** Se retira la versión vigente; la anterior ya quedó histórica al versionar.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02 |
| `<REGLA_PA>` | 02 | 03, 04 |
| `<REGLA_PA_V2>` | 04 | 05 |

[Empezar → paso 01](01-consultar-pais-y-reglas.md)
