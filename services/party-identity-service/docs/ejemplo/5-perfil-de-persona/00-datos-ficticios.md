# Datos del ejercicio — Ejercicio 5 — Perfil de contacto de una persona: cliente persona natural e inactivación

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Persona | LUIS CLIENTE FICTICIO — `CC 1000000005` (**ficticios**), nacido en 1985 |
| Contacto | `luis.cliente@correo-ficticio.co`, `+57 300 555 0105` (**ficticios**) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Sin dirección | Basta uno de correo, teléfono o dirección; sin geografía no se consulta Geography. |
| Sin cascadas | Inactivar la persona no cierra su perfil: solo impide versiones nuevas (DS-07). |
| Permiso específico | Leer la persona (`person_identities:read`) **no** permite leer su contacto: hace falta `person_contact_profiles:read`. |

[Empezar → paso 01](01-consultar-referencias.md)
