# Datos del ejercicio — Ejercicio 4 — Usuarios operativos de una empresa

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Empresa A | COMERCIALIZADORA USUARIOS FICTICIA S.A.S. (**ficticia**) |
| Empresa B | ALIADO USUARIOS FICTICIO S.A.S. (**ficticia**) |
| Persona 1 | Supervisora ficticia; cuenta de Keycloak `supervisor.test` |
| Persona 2 | Comprador ficticio; cuenta de Keycloak `compras.test` |
| Cuenta técnica | `service-account-inventory-service` (cuenta de servicio de un cliente `client_credentials`) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Membresía | Un usuario operativo es la pertenencia de **una persona humana** (cuenta de Keycloak + `PersonIdentity`) a **una** empresa. La misma persona puede estar en varias empresas. |
| Cuenta | Se indica por `username` o por `keycloak_user_id` (`sub`); el servicio la verifica en Keycloak y guarda solo el `sub` (DS-03). |
| Persona | `person_identity_id` es obligatorio y debe estar `ACTIVE` en Party Identity (DS-16). |
| Unicidad | Como máximo una membresía `ACTIVE` por empresa y persona, y por empresa y cuenta; el historial se conserva (DS-01). |
| Aislamiento | Desde que `supervisor.test` es miembro de la empresa A, puede consultarla; los demás usuarios sin membresía reciben `404`. |

[Empezar → paso 01](01-consultar-personas.md)
