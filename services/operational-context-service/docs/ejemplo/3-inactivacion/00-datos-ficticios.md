# Datos del ejercicio — Ejercicio 3 — Inactivar y reactivar una empresa

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | SERVICIOS EJEMPLO FICTICIOS S.A.S. (**ficticia**) |
| Sucursal | `CEN-01` Oficina Centro (**ficticia**) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Inactivar | Cambia `status` a `INACTIVE`; la empresa sigue consultable y **no** se elimina (D7). |
| Sin cascada | Las sucursales conservan su propio `status`; su respuesta informa `company_status` (DS-07). |
| Consumidores | Una sucursal sirve para nuevas operaciones solo si `status` y `company_status` son `ACTIVE`. |
| Permisos | Inactivar exige `delete`; reactivar exige `update` (DS-11). |

[Empezar → paso 01](01-consultar-organizacion.md)
