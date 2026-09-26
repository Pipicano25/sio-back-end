# Datos del ejercicio — Ejercicio 3 — Organizaciones: registrar, rechazos, inactivar y reactivar

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Razón social | COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. (**ficticia**) |
| NIT | `900000001-1` (**ficticio**; cumple el formato número-guion-dígito, no es un NIT real) |
| NIT mal escrito (rechazo) | `900000001` sin guion ni dígito de verificación |
| País inexistente (rechazo) | `5e0c0f6e-0000-4000-8000-00000000dead` (UUID ficticio que Geography no conoce) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Regla aplicada | La regla `NIT` de organizaciones exige `^[A-Z0-9]{4,11}-[0-9]$`. |
| País | Se valida contra Geography: si no existe responde `422 COUNTRY_NOT_FOUND`; si Geography no responde, `503`. |
| `registration_status` | Es el estado legal informativo; **no** controla el uso. El uso lo controla `status`. |
| Datos legales | En un entorno real el NIT y la razón social se toman del RUT o del registro mercantil (RUES); nunca se inventan: el registro es global. |

[Empezar → paso 01](01-consultar-pais.md)
