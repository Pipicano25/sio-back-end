# Datos del ejercicio — Ejercicio 5 — Sucursales asignadas y acceso operativo

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Empresa | LOGÍSTICA ACCESO FICTICIA S.A.S. (**ficticia**) |
| Sucursales | `PRI-01` Principal y `SEC-01` Secundaria (**ficticias**) |
| Usuario | `compras.test` (grupo `compras`: `perm:purchase:all:all`, lecturas) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Acceso efectivo | Se calcula en cada consulta: membresía, empresa, sucursal y asignación `ACTIVE` y, si se indica, el permiso de la operación. Una sola condición fallida niega el acceso (DS-07). |
| Respuesta | Siempre `200` con `allowed` y una causa estable (`reason`); `4xx`/`5xx` solo para errores de contrato (DS-08). |
| Vía técnica | Con `keycloak_user_id` exige `platform:lookup`; el permiso se evalúa con los roles del usuario leídos de Keycloak, nunca con los del token que consulta (R-11). |
| Autor | `assigned_by` es siempre el `sub` de quien asigna (DS-10). |

[Empezar → paso 01](01-consultar-datos.md)
