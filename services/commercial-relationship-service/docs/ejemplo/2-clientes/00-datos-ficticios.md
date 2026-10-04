# Datos del ejercicio — Ejercicio 2 — Clientes persona y organización

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para clientes y proveedores. Las personas, organizaciones y empresas de este ejercicio son **inventadas** y no corresponden a entidades reales. Commercial Relationship no guarda NIT, razón social ni documentos: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Empresa | COMERCIALIZADORA CLIENTES FICTICIA S.A.S. (**ficticia**) |
| Cliente persona | Persona **ficticia** registrada en Party Identity (documento ficticio) |
| Cliente organización | MINIMARKET EJEMPLO FICTICIO S.A.S. (**ficticio**, NIT ficticio) |
| Contacto preferido | Persona de contacto **ficticia** de esa organización |
| Otra organización | DISTRIBUIDORA AJENA FICTICIA S.A.S. (**ficticia**) con su propio contacto |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Fuente | No existe una fuente del sistema anterior para clientes: todos los datos son **ficticios**. Ningún NIT, razón social ni documento se presenta como real. |
| Qué se guarda | Solo el `id` de la identidad en Party Identity, el código interno y el nombre visible de la empresa. Nombre legal, documento y contacto se consultan en Party Identity (Principio III). |
| Tipo | `PERSON` exige `person_identity_id`; `ORGANIZATION` exige `organization_identity_id`; nunca ambos. |
| Contacto | Solo organizaciones; debe ser de la misma organización y estar activo al asignarlo. |
| Propia empresa | Una empresa no puede ser cliente de sí misma (DS-15). |

[Empezar → paso 01](01-consultar-identidades.md)
