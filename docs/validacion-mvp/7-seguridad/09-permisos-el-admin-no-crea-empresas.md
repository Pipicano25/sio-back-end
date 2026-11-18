# Paso 09 de 12 — Permisos: el Admin no crea empresas

Ejercicio 7 — Seguridad entre empresas y permisos · [Orden del ejercicio](ORDEN.md)

---

## 1. admin.dao (Admin) intenta crear una empresa

Paso `S-03` · usuario **`admin.dao`** · ítems de la FASE 10: 21

```http
POST http://127.0.0.1:8104/api/v1/companies
```

```json
{}
```

**Permiso que exige la URL:** `perm:operational-context:platform:administer`

- ✅ **Pueden:** `admin.sio` (por `perm:all:all:all`)

**Respuesta esperada:** `403`
