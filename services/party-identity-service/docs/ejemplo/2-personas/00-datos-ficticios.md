# Datos del ejercicio — Ejercicio 2 — Personas: registrar, validar, verificar e inactivar

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Nombre | ANA MARIA EJEMPLO FICTICIA (**ficticio**) |
| Documento | `CC 1000000001` (**ficticio**; cumple el formato de 10 dígitos de la cédula moderna) |
| Fecha de nacimiento | 1990-05-10 (adulta) |
| Menor de edad (rechazo) | `TI 1000000002` con la misma fecha de nacimiento (**ficticio**) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Reglas aplicadas | `CC` tiene dos reglas activas (moderna y antigua): el número debe cumplir al menos una; ambas exigen 18 años o más, así que `birth_date` es obligatoria. |
| Tarjeta de identidad | `TI` exige de 7 a 17 años: una persona de 1990 responde `422 AGE_OUT_OF_RANGE`. |
| Estados | `verification_status` (verificación) y `status` (uso) son independientes: inactivar no cambia la verificación. |
| Datos sensibles | El número completo y la fecha solo se devuelven a quien tiene permiso de lectura; en logs y mensajes de error se enmascaran (`******0001`). |

[Empezar → paso 01](01-consultar-pais.md)
