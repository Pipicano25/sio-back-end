# Datos del ejercicio — Ejercicio 7 — Sectores económicos: árbol CIIU, catálogo propio y sectores de una organización

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Catálogo CIIU | Datos **oficiales** del DANE (CIIU Rev. 5 A.C.), cargados con `python -m party_identity_service.seed load-business-sectors`; no son ficticios |
| Clasificación propia | `EJEMPLO_INTERNO`, códigos `X` y `X1` (**ficticios**) |
| Organización | CAFE Y TIENDA FICTICIA S.A.S. — NIT `900000007-7` (**ficticios**) |
| Sectores asignados | Clase CIIU `0123` (Cultivo de café) y clase `4711` (comercio al por menor de alimentos) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Árbol | `parent_sector_id` une clase → grupo → división → sección; las secciones no tienen padre (`level_root=true`). |
| Identidad del sector | `classification_system` + `code` es única e inmutable; varias clasificaciones conviven en el mismo catálogo. |
| Inactivación | Un sector con hijos `ACTIVE` no se inactiva (`409 SECTOR_HAS_ACTIVE_CHILDREN`): primero los hijos; no hay cascada. |
| Sector principal | Como máximo uno vigente por organización; se cambia con `set-primary`. |
| Vigencia | Las asignaciones usan `[valid_from, valid_to)`; cerradas no se reactivan: se crea una nueva. |

[Empezar → paso 01](01-recorrer-arbol-ciiu.md)
