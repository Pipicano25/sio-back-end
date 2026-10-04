# Datos del ejercicio — Ejercicio 3 — Proveedores, bloqueo y desbloqueo

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para clientes y proveedores. Las personas, organizaciones y empresas de este ejercicio son **inventadas** y no corresponden a entidades reales. Commercial Relationship no guarda NIT, razón social ni documentos: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Empresa | DISTRIBUIDORA PROVEEDORES FICTICIA S.A.S. (**ficticia**) |
| Proveedor 1 | LABORATORIO EJEMPLO FICTICIO S.A.S. (**ficticio**, NIT ficticio) |
| Proveedor 2 | IMPORTADORA EJEMPLO FICTICIA S.A.S. (**ficticia**), también cliente de la empresa |
| Motivo de bloqueo | "Incumplimiento de entregas (ficticio)" |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Fuente | No existe una fuente del sistema anterior para proveedores: los datos son **ficticios**. |
| Solo organizaciones | Un proveedor es siempre una `OrganizationIdentity`; nunca la propia empresa. |
| Bloqueo | `BLOCKED` es una decisión de la empresa, distinta de `INACTIVE`: exige motivo y se sale de él solo desbloqueando. Bloquear exige `delete` (como inactivar); desbloquear exige `update`. |
| Cliente y proveedor | Una organización puede ser a la vez cliente y proveedor: son relaciones independientes. |
| Edición | El `PUT` se permite en cualquier estado y nunca cambia el estado ni el motivo (DS-17). |

[Empezar → paso 01](01-consultar-organizaciones.md)
