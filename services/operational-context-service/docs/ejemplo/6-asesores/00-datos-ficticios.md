# Datos del ejercicio — Ejercicio 6 — Asesores de la empresa

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Empresa | ASESORADA EJEMPLO FICTICIA S.A.S. (**ficticia**) |
| Asesor 1 | Primer asesor principal (persona **ficticia**) |
| Asesor 2 | Nuevo asesor principal (persona **ficticia**) |
| Asesor 3 | Asesor no principal (persona **ficticia**) |
| Vigencias | Fechas pasadas fijas, para que el historial sea reproducible |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Asesor | Persona de Party Identity relacionada con la empresa con vigencia; no exige cuenta en SIO. |
| Principal | Como máximo un asesor principal vigente por empresa; puede haber varios no principales. |
| Cambio | `change-primary` cierra la asignación vigente y crea la nueva en una sola transacción; nunca sobrescribe la persona de una asignación (DS-13). |
| Validación | La persona se valida en Party Identity al crear y en el cambio, antes de escribir (DS-15). |

[Empezar → paso 01](01-consultar-datos.md)
