# Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar el contacto comercial (vinculado a una persona identificada) como **principal** y el de cartera, ver el `409` al crear un segundo principal, cambiarlo con **`set-primary`** (atómico) y **inactivar** un contacto sin afectar a los demás. El `GET` por `id` es el contrato Provider que usará Commercial Relationship para validar el contacto preferido de un cliente o proveedor.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-pais.md](01-consultar-pais.md) | Obtener `<PAIS_CO>`. | 1 | — |
| 02 | [02-registrar-identidades.md](02-registrar-identidades.md) | Crear las identidades globales. | 2 | 01 |
| 03 | [03-registrar-contactos.md](03-registrar-contactos.md) | Crear el principal y el de cartera. | 3 | 02 |
| 04 | [04-set-primary-e-inactivar.md](04-set-primary-e-inactivar.md) | Usar set-primary y retirar un contacto. | 4 | 02, 03 |

## Por qué este orden

1. **Identidades primero.** La organización y la persona vinculada deben existir y estar `ACTIVE`.
2. **Principal antes de cambiarlo.** El `409` y el `set-primary` se ven después de tener un principal.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PAIS_CO>` | 01 | 02 |
| `<ORG_LAB>` | 02 | 03, 04 |
| `<PERSONA_MARTA>` | 02 | 03 |
| `<CONTACTO_COMERCIAL>` | 03 | 04 |
| `<CONTACTO_CARTERA>` | 03 | 04 |

[Empezar → paso 01](01-consultar-pais.md)
