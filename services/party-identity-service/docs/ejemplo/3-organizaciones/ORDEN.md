# Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar una organización con NIT, los rechazos por **formato** (regla `NIT`) y por **país inexistente**, y el ciclo **inactivar → reactivar**, incluido el rechazo de una transición repetida y quién puede hacer cada acción (`supervisor.test` reactiva pero no inactiva).

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-pais.md](01-consultar-pais.md) | Obtener `<PAIS_CO>`. | 1 | — |
| 02 | [02-registrar-organizacion.md](02-registrar-organizacion.md) | Crear la organización y comprobar los rechazos. | 3 | 01 |
| 03 | [03-inactivar-y-reactivar.md](03-inactivar-y-reactivar.md) | Retirar la organización de uso y volver a activarla. | 4 | 02 |

## Por qué este orden

1. **País primero.** La organización lleva el `id` del país de registro.
2. **Inactivar antes de reactivar.** Reactivar una organización activa responde `409 INVALID_STATUS_TRANSITION`.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02 |
| `<ORG_EJEMPLO>` | 02 | 03 |

[Empezar → paso 01](01-consultar-pais.md)
