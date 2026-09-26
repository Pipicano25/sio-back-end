# Ejercicio 2 — Sucursales de una empresa

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar sucursales con **código único por empresa**, la **zona horaria heredada** frente a la propia, los rechazos por **código duplicado** y por **ubicación incoherente**, y el **cambio de código** (las referencias usan el `id`, no el código).

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-organizacion.md](01-consultar-organizacion.md) | Obtener `<ORG_EMPRESA>`. | 1 | — |
| 02 | [02-consultar-ubicacion.md](02-consultar-ubicacion.md) | Obtener `<PAIS_CO>`, `<DIV_ANT>`, `<CIU_MED>`, `<DIV_CUN>` y `<CIU_BOG>`. | 5 | — |
| 03 | [03-registrar-empresa.md](03-registrar-empresa.md) | Crear la empresa que tendrá las sucursales. | 1 | 01, 02 |
| 04 | [04-registrar-sucursales.md](04-registrar-sucursales.md) | Crear dos sucursales y comprobar los rechazos. | 4 | 02, 03 |
| 05 | [05-consultar-y-cambiar-codigo.md](05-consultar-y-cambiar-codigo.md) | Listar las sucursales de la empresa y cambiar el código de la bodega. | 3 | 02, 03, 04 |

## Por qué este orden

1. **Empresa primero.** Las sucursales se crean bajo `/api/v1/companies/<EMPRESA>/branches`.
2. **Ubicación antes de las sucursales.** Se consultan en Geography los `id` que se envían.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<ORG_EMPRESA>` | 01 | 03 |
| `<PAIS_CO>` | 02 | 03, 04, 05 |
| `<DIV_ANT>` | 02 | 04 |
| `<CIU_MED>` | 02 | 04 |
| `<DIV_CUN>` | 02 | 04, 05 |
| `<CIU_BOG>` | 02 | 04, 05 |
| `<EMPRESA>` | 03 | 04, 05 |
| `<SUC_MED>` | 04 | — |
| `<SUC_BOG>` | 04 | 05 |

[Empezar → paso 01](01-consultar-organizacion.md)
