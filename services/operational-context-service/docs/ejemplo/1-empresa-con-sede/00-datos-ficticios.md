# Datos del ejercicio — Ejercicio 1 — Empresa con su sede operativa principal

[← Orden del ejercicio](ORDEN.md)

> **Datos ficticios.** No existe una fuente del sistema anterior para empresas y sucursales. Los nombres, direcciones, correos, teléfonos y organizaciones de este ejercicio son **inventados** y no corresponden a empresas reales. La empresa no guarda NIT ni razón social: esos datos legales viven en Party Identity y en un entorno real se toman de una fuente oficial (RUT, registro mercantil RUES).

## Datos usados

| Dato | Valor |
| --- | --- |
| Organización | COMERCIALIZADORA EJEMPLO FICTICIA S.A.S. (**ficticia**), ya registrada en Party Identity |
| Correo y teléfono de la sede | `contacto@comercializadora-ficticia.co`, `+57 604 000 0001` (**ficticios**) |
| Dirección de la sede | Carrera Ficticia 43A # 1-50, Medellín (**ficticia**) |
| Coordenadas | `6.208000`, `-75.567000` (aproximadas, ilustrativas) |
| Organización inexistente (rechazo) | `7a1c0f10-0000-4000-8000-00000000dead` (UUID que Party Identity no conoce) |

## Cómo se interpretan

| Tema | Decisión |
| --- | --- |
| Identidad legal | La empresa **no guarda** NIT, razón social ni nombre comercial: se consultan en Party Identity con `organization_identity_id` (DS-01, DS-13). |
| Contacto | Correo, teléfono y dirección son de la **sede operativa principal** en SIO; no son el contacto global de la organización (DS-14). |
| Ubicación | País, departamento y ciudad son `id` de Geography; se validan juntos y deben ser coherentes. |
| Zona horaria y moneda | Si no se envían, la empresa queda con `America/Bogota` y `COP`. |

[Empezar → paso 01](01-consultar-organizacion.md)
