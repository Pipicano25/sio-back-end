# Ejercicio 5 — Sucursales asignadas y acceso operativo

[← Todos los ejercicios](../README.md)

**Qué enseña:** Asignar sucursales a un usuario operativo y comprobar su **acceso operativo** con `GET /api/v1/operational-access`: permitido, cada **causa estable** de denegación y la **vía técnica** que evalúa el permiso con los roles del usuario objetivo.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-datos.md](01-consultar-datos.md) | Obtener `<ORG_EMPRESA>` y `<PERSONA_COMPRADOR>`. | 2 | — |
| 02 | [02-empresa-y-sucursales.md](02-empresa-y-sucursales.md) | Crear la empresa, dos sucursales y la membresía de `compras.test`. | 4 | 01 |
| 03 | [03-asignar-sucursal.md](03-asignar-sucursal.md) | Asignar `PRI-01` al usuario y ver su acceso calculado. | 3 | 02 |
| 04 | [04-comprobar-acceso.md](04-comprobar-acceso.md) | Consultar el acceso de `compras.test` como lo haría Purchase con su identidad técnica. | 3 | 02 |
| 05 | [05-efecto-de-inactivar.md](05-efecto-de-inactivar.md) | Retirar la asignación, inactivar la sucursal y volver a comprobar. | 4 | 02, 03 |

## Por qué este orden

1. **Membresía antes de asignar.** Solo se asignan sucursales de la empresa de la membresía.
2. **Asignar antes de consultar el acceso.** Sin asignación la causa es `BRANCH_NOT_ASSIGNED`.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<ORG_EMPRESA>` | 01 | 02 |
| `<PERSONA_COMPRADOR>` | 01 | 02 |
| `<EMPRESA>` | 02 | — |
| `<SUC_PRINCIPAL>` | 02 | 03, 04, 05 |
| `<SUC_SECUNDARIA>` | 02 | 04 |
| `<USR_COMPRADOR>` | 02 | 03 |
| `<ASIGNACION>` | 03 | 05 |

[Empezar → paso 01](01-consultar-datos.md)
