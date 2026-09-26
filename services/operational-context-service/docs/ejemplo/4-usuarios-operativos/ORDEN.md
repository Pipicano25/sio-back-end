# Ejercicio 4 — Usuarios operativos de una empresa

[← Todos los ejercicios](../README.md)

**Qué enseña:** Registrar **usuarios operativos** (membresías): la cuenta de Keycloak por `username` o `sub`, la persona en Party Identity, una sola membresía `ACTIVE` por empresa, la **misma persona en dos empresas**, el rechazo de una **cuenta técnica** y la inactivación y reactivación sin afectar la otra empresa.

**Datos:** **ficticios** — detalle y decisiones en [00-datos-ficticios.md](00-datos-ficticios.md).

Antes de empezar revise los [requisitos comunes](../README.md#antes-de-empezar).

**Usuarios:** ejecútelo con `admin.test`. Qué puede hacer cada usuario de prueba, qué permiso exige cada URL y ejemplos de uso con cada uno: [USUARIOS.md](USUARIOS.md).

## Orden de ejecución

Ejecute los archivos **en este orden**. Cada paso usa `id` guardados en pasos anteriores.

| Paso | Archivo | Qué hace | Llamadas | Depende de |
| --- | --- | --- | --- | --- |
| 00 | [00-datos-ficticios.md](00-datos-ficticios.md) | Leer: los datos ficticios y cómo se interpretan | — | — |
| 01 | [01-consultar-personas.md](01-consultar-personas.md) | Obtener `<PERSONA_SUPERVISORA>` y `<PERSONA_COMPRADOR>`. | 2 | — |
| 02 | [02-registrar-empresas.md](02-registrar-empresas.md) | Crear las empresas A y B (solo el administrador de plataforma). | 4 | — |
| 03 | [03-registrar-usuarios.md](03-registrar-usuarios.md) | Registrar a la supervisora por `username` y comprobar los rechazos. | 4 | 01, 02 |
| 04 | [04-consultar-usuarios.md](04-consultar-usuarios.md) | Listar las membresías y consultar una por su `id`. | 2 | 02, 03 |
| 05 | [05-misma-persona-otra-empresa.md](05-misma-persona-otra-empresa.md) | Registrar a `compras.test` también en la empresa B y retirarlo solo de esa empresa. | 4 | 01, 02, 03 |

## Por qué este orden

1. **Persona y empresas primero.** La membresía une una empresa existente con una persona de Party Identity.
2. **Registrar antes de inactivar.** La reactivación vuelve a validar la cuenta y la persona.

## Lista de `id` que debe ir guardando

| Variable | Se obtiene en | Se usa en |
| --- | --- | --- |
| `<PERSONA_SUPERVISORA>` | 01 | 03 |
| `<PERSONA_COMPRADOR>` | 01 | 03, 05 |
| `<ORG_A>` | 02 | — |
| `<ORG_B>` | 02 | — |
| `<EMPRESA_A>` | 02 | 03, 04 |
| `<EMPRESA_B>` | 02 | 05 |
| `<USR_SUPERVISORA>` | 03 | 04 |
| `<USR_COMPRADOR_A>` | 03 | 05 |
| `<USR_COMPRADOR_B>` | 05 | — |

[Empezar → paso 01](01-consultar-personas.md)
