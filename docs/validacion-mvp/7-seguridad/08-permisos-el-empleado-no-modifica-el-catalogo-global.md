# Paso 08 de 12 — Permisos: el empleado no modifica el catálogo global

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. compras.test (Empleado) intenta crear una categoría del catálogo global

Paso `S-02` · usuario **`compras.test`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8103/api/v1/categories
```

```json
{}
```

**Permiso que exige la URL:** `perm:product-catalog:categories:create`

- ✅ **Pueden:** `admin.test` (por `perm:all:all:all`), `supervisor.test` (por `perm:product-catalog:all:create`)

**Respuesta esperada:** `403`
