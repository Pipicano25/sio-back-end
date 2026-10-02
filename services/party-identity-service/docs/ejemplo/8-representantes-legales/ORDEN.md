# Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre

[← Todos los ejercicios](../README.md)

**Qué enseña:** Establecer el **primer** representante `PRIMARY` con `set-primary`, ver el `409` al registrar otro `PRIMARY` por el alta ordinaria, **sustituirlo** con `set-primary` (cierra el anterior y crea el nuevo), registrar un suplente con su **referencia documental** y cerrarlo. Es un dato sensible: `compras.test` recibe `403`.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-pais.md](01-consultar-pais.md) | Obtener `<PAIS_CO>`. | 1 | — |
| 02 | [02-registrar-identidades.md](02-registrar-identidades.md) | Crear las identidades. | 3 | 01 |
| 03 | [03-establecer-primary.md](03-establecer-primary.md) | Usar set-primary y ver el conflicto. | 3 | 02 |
| 04 | [04-suplente-y-cierre.md](04-suplente-y-cierre.md) | Registrar un suplente y cerrarlo. | 3 | 02 |

## Por qué este orden

1. **Identidades primero.** Organización y personas deben existir y estar `ACTIVE`.
2. **PRIMARY antes de sustituirlo.** La sustitución envía `current_primary_version` del `PRIMARY` vigente.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02 |
| `<ORG_INV>` | 02 | 03, 04 |
| `<PERSONA_JORGE>` | 02 | 03, 04 |
| `<PERSONA_ELENA>` | 02 | 03 |
| `<REP_JORGE>` | 03 | — |
| `<REP_ELENA>` | 03 | — |
| `<REP_JORGE_SUPLENTE>` | 04 | — |

[Empezar → paso 01](01-consultar-pais.md)
