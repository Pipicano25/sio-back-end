# Ejercicio 3 — Proveedores, bloqueo y desbloqueo

[← Todos los ejercicios](../README.md)

**Qué enseña:** Seleccionar **proveedores**, usar la **misma organización como cliente y proveedor**, **bloquear** con motivo (solo `admin.test`), ver la **transición inválida** de un proveedor bloqueado, **modificarlo sin desbloquearlo** y **desbloquearlo**.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-organizaciones.md](01-consultar-organizaciones.md) | Obtener `<EMPRESA>` y las dos organizaciones. | 3 | — |
| 02 | [02-seleccionar-proveedores.md](02-seleccionar-proveedores.md) | Registrar dos proveedores, uno de ellos también cliente. | 4 | 01 |
| 03 | [03-bloquear.md](03-bloquear.md) | Bloquear con motivo y ver las transiciones válidas. | 3 | 02 |
| 04 | [04-desbloquear-y-consultar.md](04-desbloquear-y-consultar.md) | Desbloquear, inactivar el segundo proveedor y consultar. | 3 | 01, 02 |

## Por qué este orden

1. **Organizaciones primero.** El proveedor referencia una organización existente en Party Identity.
2. **Bloquear antes de desbloquear.** El desbloqueo solo es válido desde `BLOCKED`.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<EMPRESA>` | 01 | 02, 04 |
| `<ORG_PROVEEDOR>` | 01 | 02 |
| `<ORG_PROVEEDOR_2>` | 01 | 02 |
| `<PROVEEDOR>` | 02 | 03, 04 |
| `<PROVEEDOR_2>` | 02 | 04 |

[Empezar → paso 01](01-consultar-organizaciones.md)
