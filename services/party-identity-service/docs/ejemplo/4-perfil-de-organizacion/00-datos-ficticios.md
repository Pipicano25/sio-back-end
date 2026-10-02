# Datos del ejercicio — Ejercicio 4 — Perfil de contacto de una organización: versiones, no-op y cierre

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | DISTRIBUIDORA CONTACTO FICTICIA S.A.S. — NIT `900000004-4` (**ficticios**) |
| Correo y teléfono | `compras@distribuidora-ficticia.co`, `+57 601 555 0104` (**ficticios**) |
| Dirección | Calle 00 # 00-04, Bogotá (**ficticia**) |
| Empresa confirmante | La empresa de Operational Context en la que el usuario tiene membresía `ACTIVE` |
| Empresa sin membresía (rechazo) | `6a1d0000-0000-4000-8000-000000000002` (**ficticia**; el usuario no es miembro) |
| Empresa con Operational Context caído (rechazo) | `6a1d0000-0000-4000-8000-000000000003` (**simulación** de indisponibilidad) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Perfil global | El perfil pertenece a la organización, no a la empresa: cualquier empresa reutiliza la versión vigente. Empresa y usuario confirmantes son **trazabilidad** de la versión, no propiedad exclusiva. |
| Versionado | Nunca se sobrescribe: un cambio cierra la vigente (`valid_to`) y crea otra en la misma operación; `version` crece por organización y se envía para reemplazar o cerrar. |
| Confirmante | `confirmed_by_user_id` nunca se envía: lo resuelve Party Identity con Operational Context (membresía `ACTIVE`). Un administrador de plataforma sin membresía recibe `422`. |
| Datos sensibles | Correo, teléfono y dirección se leen con el permiso específico `organization_contact_profiles:read`; en logs y errores se enmascaran. |

[Empezar → paso 01](01-consultar-referencias.md)
