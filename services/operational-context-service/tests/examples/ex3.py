"""Ejercicio 3 de docs/ejemplo/: inactivación de empresa y efecto en sus sucursales (FR-017, FR-026, DS-07, DS-11)."""

from tests.examples.spec_common import API, ORG_EJ3, call, get_organization, step

EX3 = dict(
    folder="3-inactivacion",
    title="Ejercicio 3 — Inactivar y reactivar una empresa",
    focus=(
        "Inactivar una empresa **sin eliminarla ni modificar sus sucursales**, ver cómo la sucursal informa el estado "
        "de su empresa, el rechazo al crear sucursales bajo una empresa inactiva, la reactivación y la transición "
        "repetida; quién puede cada acción (`supervisor.test` reactiva pero no inactiva)."
    ),
    data=[
        ("Organización", "SERVICIOS EJEMPLO FICTICIOS S.A.S. (**ficticia**)"),
        ("Sucursal", "`CEN-01` Oficina Centro (**ficticia**)"),
    ],
    interpretation=[
        ("Inactivar", "Cambia `status` a `INACTIVE`; la empresa sigue consultable y **no** se elimina (D7)."),
        ("Sin cascada", "Las sucursales conservan su propio `status`; su respuesta informa `company_status` (DS-07)."),
        ("Consumidores", "Una sucursal sirve para nuevas operaciones solo si `status` y `company_status` son `ACTIVE`."),
        ("Permisos", "Inactivar exige `delete`; reactivar exige `update` (DS-11)."),
    ],
    order_rules=[
        ("Empresa y sucursal antes de inactivar", "El efecto se observa en la sucursal existente."),
        ("Inactivar antes de reactivar", "Reactivar una empresa activa responde `409 INVALID_STATUS_TRANSITION`."),
    ],
    steps=[
        step("01-consultar-organizacion.md", "Consultar la organización", "Obtener `<ORG_EMPRESA>`.",
             [get_organization("ORG_EMPRESA", ORG_EJ3, "SERVICIOS EJEMPLO FICTICIOS S.A.S.")]),
        step("02-registrar-empresa-y-sucursal.md", "Registrar la empresa y su sucursal",
             "Crear la empresa y una sucursal activa.", [
                 call("Registrar la empresa", "POST", f"{API}/companies",
                      body={"organization_identity_id": "<ORG_EMPRESA>"},
                      why=["Empresa mínima: solo la organización."],
                      save={"EMPRESA": "id"}, show=["id", "status", "version"]),
                 call("Registrar la sucursal", "POST", f"{API}/companies/<EMPRESA>/branches",
                      body={"code": "CEN-01", "name": "Oficina Centro (ficticia)"},
                      why=["Sucursal sin ubicación: todos los campos de ubicación son opcionales."],
                      save={"SUCURSAL": "id"}, show=["id", "code", "status", "company_status"]),
             ]),
        step(
            "03-inactivar-empresa.md",
            "Inactivar la empresa",
            "Inactivar la empresa y ver el efecto en su sucursal.",
            [
                call("Inactivar la empresa con la versión vigente", "POST", f"{API}/companies/<EMPRESA>/deactivate",
                     body={"version": 1},
                     why=["Exige el permiso `delete` aunque no elimina: cambia `status` a `INACTIVE`."],
                     show=["status", "version"]),
                call("Consultar la sucursal", "GET", f"{API}/branches/<SUCURSAL>",
                     why=["La sucursal sigue `ACTIVE`, pero informa `company_status: INACTIVE`: los consumidores no "
                          "deben usarla para nuevas operaciones."],
                     show=["status", "company_status", "version"]),
                call("Intentar crear otra sucursal (rechazado)", "POST", f"{API}/companies/<EMPRESA>/branches",
                     body={"code": "CEN-02", "name": "Oficina Norte (ficticia)"},
                     why=["No se crean sucursales bajo una empresa inactiva: `422 COMPANY_INACTIVE`."],
                     expect=422, show=["status", "code", "detail"]),
            ],
        ),
        step(
            "04-reactivar-empresa.md",
            "Reactivar la empresa",
            "Reactivar la empresa y comprobar la transición repetida.",
            [
                call("Reactivar la empresa", "POST", f"{API}/companies/<EMPRESA>/reactivate", body={"version": 2},
                     why=["Exige el permiso `update`; por eso `supervisor.test` puede reactivar."],
                     show=["status", "version"]),
                call("Intentar reactivarla otra vez (rechazado)", "POST", f"{API}/companies/<EMPRESA>/reactivate",
                     body={"version": 3},
                     why=["Ya está `ACTIVE`: `409 INVALID_STATUS_TRANSITION`, sin cambiar la versión."],
                     expect=409, show=["status", "code", "detail"]),
                call("Consultar la sucursal otra vez", "GET", f"{API}/branches/<SUCURSAL>",
                     why=["Con la empresa activa, la sucursal vuelve a estar disponible sin haberla modificado."],
                     show=["status", "company_status", "version"]),
            ],
        ),
    ],
)
