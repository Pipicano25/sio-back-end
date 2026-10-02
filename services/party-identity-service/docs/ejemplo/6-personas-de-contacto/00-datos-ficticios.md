# Datos del ejercicio — Ejercicio 6 — Personas de contacto: principal, set-primary e inactivación

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | LABORATORIO CONTACTOS FICTICIO S.A.S. — NIT `900000006-6` (**ficticios**) |
| Contacto comercial | MARTA COMERCIAL FICTICIA — `CC 1000000006` (**ficticia**) |
| Contacto de cartera | Teléfono `+57 601 555 0166` (**ficticio**), sin persona identificada |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Principal único | Como máximo un contacto activo principal por organización; puede no haber ninguno. |
| Cambio de principal | Solo con `:set-primary` (desmarca el anterior y marca el nuevo en una operación); `is_primary` no se cambia con `PUT` (`422 IMMUTABLE_FIELD`). |
| Inactivar | Quita la marca de principal solo de ese contacto; los demás no cambian. |

[Empezar → paso 01](01-consultar-pais.md)
