# Ejercicio 1 — Empresa con su sede operativa principal

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar una empresa **vinculada a su identidad legal** de Party Identity, con la ubicación coherente de su **sede operativa principal**; consultarla y modificarla con control de **versión**; y el rechazo cuando la organización no existe.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-organizacion.md](01-consultar-organizacion.md) | Obtener `<ORG_EMPRESA>`. | 1 | — |
| 02 | [02-consultar-ubicacion.md](02-consultar-ubicacion.md) | Obtener `<PAIS_CO>`, `<DIV_ANT>` y `<CIU_MED>`. | 3 | — |
| 03 | [03-registrar-empresa.md](03-registrar-empresa.md) | Crear la empresa y comprobar el rechazo por organización inexistente. | 2 | 01, 02 |
| 04 | [04-consultar-y-modificar.md](04-consultar-y-modificar.md) | Leer la empresa, cambiar el teléfono con la versión vigente y buscarla por su organización. | 3 | 01, 02, 03 |

## Por qué este orden

1. **Organización primero.** La empresa exige el `id` de una organización `ACTIVE` de Party Identity.
2. **Ubicación antes de la empresa.** País → departamento → ciudad: cada consulta usa el `id` anterior.
3. **Versión.** Para modificar se envía la `version` leída; la respuesta trae la nueva.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<ORG_EMPRESA>` | 01 | 03, 04 |
| `<PAIS_CO>` | 02 | 03, 04 |
| `<DIV_ANT>` | 02 | 03, 04 |
| `<CIU_MED>` | 02 | 03, 04 |
| `<EMPRESA>` | 03 | 04 |

[Empezar → paso 01](01-consultar-organizacion.md)
