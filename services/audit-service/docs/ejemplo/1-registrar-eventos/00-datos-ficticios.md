# Datos del ejercicio 1 (ficticios)

No existe una fuente del sistema anterior para eventos de auditoría: todos los datos son **ficticios** y sus identificadores son fijos para que la documentación sea estable.

| Dato | Valor | Interpretación |
| --- | --- | --- |
| Empresa | `a11d0000-0000-4000-8000-000000000001` | Empresa ficticia de los eventos. |
| Precio de lista | `b22e0000-0000-4000-8000-000000000010` | Entidad afectada (`PriceListItem`). |
| Actor | `13fb7acf-dac0-4fba-ae39-6759c77c3f97` | `sub` de `admin.test`, el usuario que originó la acción en el emisor. |
| Emisor | `audit-test-emitter` | Cuenta de servicio de pruebas; Audit fija `source_service` con su `client_id`. |
