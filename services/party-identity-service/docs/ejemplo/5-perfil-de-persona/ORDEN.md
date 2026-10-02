# Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar el contacto de un **cliente persona natural** (sin dirección, solo correo y teléfono), consultarlo, y ver que al **inactivar la persona** el perfil sigue consultable (sin cascadas) pero no se aceptan versiones nuevas (`422 PERSON_IDENTITY_INACTIVE`).

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-referencias.md](01-consultar-referencias.md) | Obtener `<PAIS_CO>` y `<EMPRESA>`. | 2 | — |
| 02 | [02-registrar-persona-y-perfil.md](02-registrar-persona-y-perfil.md) | Crear la persona y su contacto vigente. | 3 | 01 |
| 03 | [03-inactivar-persona.md](03-inactivar-persona.md) | Ver el efecto sobre el perfil. | 3 | 01, 02 |

## Por qué este orden

1. **Referencias primero.** País y empresa confirmante se consultan en sus servicios.
2. **Persona activa.** El perfil se registra mientras la persona está `ACTIVE`; luego se inactiva para ver el efecto.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02 |
| `<EMPRESA>` | 01 | 02, 03 |
| `<PERSONA_CLIENTE>` | 02 | 03 |

[Empezar → paso 01](01-consultar-referencias.md)
