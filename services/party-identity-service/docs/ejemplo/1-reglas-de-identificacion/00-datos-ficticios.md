# Datos del ejercicio — Ejercicio 1 — Reglas de identificación: crear, versionar y retirar

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| País | Colombia (`COL`), consultado en Geography Service |
| Tipo de parte | `PERSON` |
| Tipo de identificación nuevo | `PASSPORT` con sigla `PA` (la carga inicial no trae pasaporte) |
| Patrón inicial | `^[A-Z0-9]{6,9}$`: 6 a 9 letras o dígitos |
| Patrón corregido | `^[A-Z]{2}[0-9]{6,7}$`: 2 letras y 6 o 7 dígitos |
| Ejemplos | `AB123456` (**ficticio**; no corresponde a ningún pasaporte real) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Reglas de Colombia | La carga inicial (`python -m party_identity_service.seed load`) deja 8 reglas activas; se consultan sin modificarlas. |
| Pasaporte | No existe regla `PA`: sin regla, una persona con esa sigla solo tiene validaciones base (DS-03). Crear la regla hace que se valide el formato. |
| Cambio de patrón | No se hace con `PUT`: se crea una **nueva versión** (`POST .../versions`). La anterior queda histórica (`is_active: false`, `valid_to` informado) para conservar con qué regla se validó cada dato. |
| Retiro | `POST .../deactivate` deja la regla histórica; nunca se elimina (D7). Una regla histórica no admite cambios. |

[Empezar → paso 01](01-consultar-pais-y-reglas.md)
