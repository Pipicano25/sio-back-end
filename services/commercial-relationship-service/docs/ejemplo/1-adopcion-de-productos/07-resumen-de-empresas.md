# Paso 07 de 07 — Ver el resumen de mis empresas

Ejercicio 1 — Adopción de productos del Excel · [← Paso anterior](06-consultar-y-estados.md) · [Orden del ejercicio](ORDEN.md)

**Objetivo:** Recorrer, una por página, las empresas del usuario con sus conteos (FR-046).

---

## 1. Ver la primera empresa del resumen

```http
GET /api/v1/company-summaries
```

**Permiso que exige la URL:** `perm:commercial-relationship:company_products:read`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:all:all:read`), `compras.test` (por `perm:commercial-relationship:all:read`), `ventas.test` (por `perm:commercial-relationship:all:read`), `inventario.test` (por `perm:commercial-relationship:company_products:read`), `reportes.test` (por `perm:commercial-relationship:company_products:read`), `consulta.test` (por `perm:commercial-relationship:company_products:read`)

**Por qué se hace así**

- Sin parámetros devuelve **una empresa por página** (`page_size` por defecto 1, máximo 100); para la siguiente se envía `?page=2`.
- Solo aparecen las empresas donde el usuario tiene membresía `ACTIVE` en Operational Context; no hay vista de plataforma (DS-03). Aquí el usuario es miembro de las tres empresas ficticias de los ejercicios.
- La razón social se lee en Operational Context y Party Identity y no se guarda. Los conteos de clientes y proveedores salen `null` si el usuario no tiene su permiso de lectura.

**Respuesta esperada — `200 OK`** (abreviada)

```json
{
  "items": [
    {
      "company_id": "<EMPRESA>",
      "company_status": "ACTIVE",
      "legal_name": "DROGUERÍA EJEMPLO FICTICIA S.A.S.",
      "company_products": {
        "total": 3,
        "ACTIVE": 3,
        "INACTIVE": 0
      },
      "company_customers": {
        "total": 0,
        "ACTIVE": 0,
        "INACTIVE": 0
      },
      "company_suppliers": {
        "total": 0,
        "ACTIVE": 0,
        "INACTIVE": 0,
        "BLOCKED": 0
      }
    }
  ],
  "page": 1,
  "page_size": 1,
  "total_records": 6,
  "total_pages": 6
}
```

---

[← Paso anterior](06-consultar-y-estados.md) · [Orden del ejercicio](ORDEN.md)
