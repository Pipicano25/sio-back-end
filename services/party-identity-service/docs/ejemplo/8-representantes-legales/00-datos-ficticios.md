# Datos del ejercicio — Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para identidades. Los nombres, números de documento, NIT y razones sociales de este ejercicio son **inventados** y no corresponden a personas ni empresas reales. En un entorno real se toman de una fuente oficial (documento de identidad, RUT, RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | INVERSIONES REPRESENTACION FICTICIA S.A.S. — NIT `900000008-8` (**ficticios**) |
| Representantes | `CC 1000000081` y `CC 1000000082` (**ficticios**) |
| Referencia documental | "Acta 001 de 2026 (ficticia)": solo texto, no se guarda el documento |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| PRIMARY único | Como máximo un `PRIMARY` vigente por organización; `ALTERNATE` y `OTHER` pueden ser varios. |
| set-primary | Establece el primero o sustituye el vigente en una operación; nunca dos `PUT`. |
| Vigencia | `[valid_from, valid_to)`: cerrar antes de que empiece la vigencia deja `valid_to = valid_from`. |
| Datos sensibles | Se leen con `organization_legal_representatives:read`, que solo tienen administradores y supervisores. |

[Empezar → paso 01](01-consultar-pais.md)
