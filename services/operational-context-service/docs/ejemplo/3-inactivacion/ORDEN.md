# Ejercicio 3 — Inactivar y reactivar una empresa

[← Todos los ejercicios](../README.md)

**Qué enseña:** Inactivar una empresa **sin eliminarla ni modificar sus sucursales**, ver cómo la sucursal informa el estado de su empresa, el rechazo al crear sucursales bajo una empresa inactiva, la reactivación y la transición repetida; quién puede cada acción (`supervisor.test` reactiva pero no inactiva).

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-organizacion.md](01-consultar-organizacion.md) | Obtener `<ORG_EMPRESA>`. | 1 | — |
| 02 | [02-registrar-empresa-y-sucursal.md](02-registrar-empresa-y-sucursal.md) | Crear la empresa y una sucursal activa. | 2 | 01 |
| 03 | [03-inactivar-empresa.md](03-inactivar-empresa.md) | Inactivar la empresa y ver el efecto en su sucursal. | 3 | 02 |
| 04 | [04-reactivar-empresa.md](04-reactivar-empresa.md) | Reactivar la empresa y comprobar la transición repetida. | 3 | 02 |

## Por qué este orden

1. **Empresa y sucursal antes de inactivar.** El efecto se observa en la sucursal existente.
2. **Inactivar antes de reactivar.** Reactivar una empresa activa responde `409 INVALID_STATUS_TRANSITION`.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<ORG_EMPRESA>` | 01 | 02 |
| `<EMPRESA>` | 02 | 03, 04 |
| `<SUCURSAL>` | 02 | 03, 04 |

[Empezar → paso 01](01-consultar-organizacion.md)
