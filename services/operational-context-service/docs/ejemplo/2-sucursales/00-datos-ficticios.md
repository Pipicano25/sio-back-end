# Datos del ejercicio — Ejercicio 2 — Sucursales de una empresa

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | DISTRIBUIDORA EJEMPLO FICTICIA S.A.S. (**ficticia**) |
| Sucursal 1 | `MED-01` Tienda El Poblado, Medellín (**ficticia**), sin zona horaria propia |
| Sucursal 2 | `BOG-01` Bodega Norte, Bogotá (**ficticia**), con zona horaria propia `America/Bogota` |
| Rechazo por incoherencia | Medellín enviada con el departamento de Cundinamarca |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Código | Se recortan los espacios y se pasa a mayúsculas: ` med-01 ` queda `MED-01`. Es único dentro de la empresa, también frente a sucursales inactivas. |
| Zona horaria | Si la sucursal no tiene zona propia, `effective_timezone` es la de su empresa, calculada en cada consulta; nunca se copia (DS-08). |
| Coherencia | La ciudad debe pertenecer al país **y** exactamente a la división enviada (DS-05). |
| Cambio de código | Está permitido: los demás servicios guardan el `id` de la sucursal (DS-10). |

[Empezar → paso 01](01-consultar-organizacion.md)
