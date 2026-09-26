# Ejercicio 2 — Personas: registrar, validar, verificar e inactivar

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar una persona con cédula, ver cómo se aplican las reglas de Colombia (formato y **edad**), el rechazo por **duplicado**, el control de **versión** al modificar, el estado de verificación y la **inactivación** sin borrar (la persona deja de aparecer en la lista, pero sigue consultable por `id`).

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-pais.md](01-consultar-pais.md) | Obtener `<PAIS_CO>`. | 1 | — |
| 02 | [02-registrar-persona.md](02-registrar-persona.md) | Crear la persona y comprobar los rechazos por edad y por duplicado. | 3 | 01 |
| 03 | [03-verificar-persona.md](03-verificar-persona.md) | Modificar con control de versión. | 2 | 01, 02 |
| 04 | [04-inactivar-persona.md](04-inactivar-persona.md) | Retirarla de uso sin borrarla y consultarla con filtro explícito. | 3 | 02 |

## Por qué este orden

1. **País primero.** La persona lleva el `id` del país emisor, que se obtiene de Geography.
2. **Registrar antes de modificar.** Cada modificación lleva la `version` leída.
3. **Inactivar al final.** Una persona inactiva se sigue pudiendo consultar por `id`, pero no aparece en la lista por defecto.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02, 03 |
| `<PERSONA_ANA>` | 02 | 03, 04 |

[Empezar → paso 01](01-consultar-pais.md)
