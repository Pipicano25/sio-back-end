"""Ejercicio 3 de docs/ejemplo/: proveedores y bloqueo (FR-030 a FR-035; DS-10, DS-16, DS-17)."""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ3,
    ORG_PROVEEDOR,
    ORG_PROVEEDOR_2,
    call,
    get_company,
    get_organization,
    step,
)

SUPPLIER_SHOW = ["id", "organization_identity_id", "internal_code", "display_name", "status", "block_reason", "version"]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX3 = dict(
    folder="3-proveedores",
    title="Ejercicio 3 — Proveedores, bloqueo y desbloqueo",
    data_file="00-datos-ficticios.md",
    focus=(
        "Seleccionar **proveedores**, usar la **misma organización como cliente y proveedor**, **bloquear** con motivo "
        "(solo `admin.test`), ver la **transición inválida** de un proveedor bloqueado, **modificarlo sin desbloquearlo** "
        "y **desbloquearlo**."
    ),
    data=[
        ("Empresa", "DISTRIBUIDORA PROVEEDORES FICTICIA S.A.S. (**ficticia**)"),
        ("Proveedor 1", "LABORATORIO EJEMPLO FICTICIO S.A.S. (**ficticio**, NIT ficticio)"),
        ("Proveedor 2", "IMPORTADORA EJEMPLO FICTICIA S.A.S. (**ficticia**), también cliente de la empresa"),
        ("Motivo de bloqueo", "\"Incumplimiento de entregas (ficticio)\""),
    ],
    interpretation=[
        ("Fuente", "No existe una fuente del sistema anterior para proveedores: los datos son **ficticios**."),
        ("Solo organizaciones", "Un proveedor es siempre una `OrganizationIdentity`; nunca la propia empresa."),
        ("Bloqueo", "`BLOCKED` es una decisión de la empresa, distinta de `INACTIVE`: exige motivo y se sale de él solo "
         "desbloqueando. Bloquear exige `delete` (como inactivar); desbloquear exige `update`."),
        ("Cliente y proveedor", "Una organización puede ser a la vez cliente y proveedor: son relaciones independientes."),
        ("Edición", "El `PUT` se permite en cualquier estado y nunca cambia el estado ni el motivo (DS-17)."),
    ],
    order_rules=[
        ("Organizaciones primero", "El proveedor referencia una organización existente en Party Identity."),
        ("Bloquear antes de desbloquear", "El desbloqueo solo es válido desde `BLOCKED`."),
    ],
    steps=[
        step("01-consultar-organizaciones.md", "Consultar la empresa y las organizaciones",
             "Obtener `<EMPRESA>` y las dos organizaciones.", [
                 get_company("EMPRESA", EMPRESA_EJ3, "DISTRIBUIDORA PROVEEDORES FICTICIA S.A.S."),
                 get_organization("ORG_PROVEEDOR", ORG_PROVEEDOR, "LABORATORIO EJEMPLO FICTICIO S.A.S."),
                 get_organization("ORG_PROVEEDOR_2", ORG_PROVEEDOR_2, "IMPORTADORA EJEMPLO FICTICIA S.A.S."),
             ]),
        step("02-seleccionar-proveedores.md", "Seleccionar los proveedores",
             "Registrar dos proveedores, uno de ellos también cliente.", [
                 call("Seleccionar el laboratorio como proveedor", "POST",
                      f"{API}/companies/<EMPRESA>/company-suppliers",
                      body={"organization_identity_id": "<ORG_PROVEEDOR>", "internal_code": "PRV-0001",
                            "display_name": "Laboratorio (ficticio)"},
                      why=["El servicio comprueba que la organización no sea la de la empresa y que esté `ACTIVE` en "
                           "Party Identity."],
                      save={"PROVEEDOR": "id"}, show=SUPPLIER_SHOW),
                 call("Registrar la importadora como cliente", "POST", f"{API}/companies/<EMPRESA>/company-customers",
                      body={"customer_kind": "ORGANIZATION", "organization_identity_id": "<ORG_PROVEEDOR_2>",
                            "internal_code": "CLI-0001", "display_name": "Importadora (ficticia)"},
                      why=["Primero como cliente, para mostrar que también puede ser proveedor."],
                      show=["id", "customer_kind", "internal_code"]),
                 call("Seleccionar la importadora también como proveedor", "POST",
                      f"{API}/companies/<EMPRESA>/company-suppliers",
                      body={"organization_identity_id": "<ORG_PROVEEDOR_2>", "internal_code": "PRV-0002",
                            "display_name": "Importadora (ficticia)"},
                      why=["Cliente y proveedor son relaciones independientes."],
                      save={"PROVEEDOR_2": "id"}, show=["id", "internal_code", "status"]),
                 call("Seleccionar otra vez el laboratorio (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-suppliers",
                      body={"organization_identity_id": "<ORG_PROVEEDOR>", "internal_code": "PRV-0099",
                            "display_name": "Duplicado"},
                      why=["Una empresa selecciona cada organización una sola vez: `409 DUPLICATE_SUPPLIER`."],
                      expect=409, show=ERROR_SHOW),
             ]),
        step("03-bloquear.md", "Bloquear el proveedor",
             "Bloquear con motivo y ver las transiciones válidas.", [
                 call("Bloquear el laboratorio", "POST", f"{API}/company-suppliers/<PROVEEDOR>/block",
                      body={"block_reason": "Incumplimiento de entregas (ficticio)", "version": 1},
                      why=["Bloquear exige `delete` y un motivo de 1 a 500 caracteres. No consulta Party Identity."],
                      show=SUPPLIER_SHOW),
                 call("Reactivar el proveedor bloqueado (rechazado)", "POST",
                      f"{API}/company-suppliers/<PROVEEDOR>/reactivate", body={"version": 2},
                      why=["De `BLOCKED` solo se sale desbloqueando: `409 INVALID_STATUS_TRANSITION`."],
                      expect=409, show=ERROR_SHOW),
                 call("Corregir el nombre visible sin desbloquear", "PUT", f"{API}/company-suppliers/<PROVEEDOR>",
                      body={"internal_code": "PRV-0001", "display_name": "Laboratorio Norte (ficticio)",
                            "preferred_contact_person_id": None, "version": 2},
                      why=["El `PUT` se permite sobre un proveedor `BLOCKED` y no cambia ni el estado ni el motivo "
                           "(DS-17)."],
                      show=["id", "display_name", "status", "block_reason", "version"]),
             ]),
        step("04-desbloquear-y-consultar.md", "Desbloquear e inactivar",
             "Desbloquear, inactivar el segundo proveedor y consultar.", [
                 call("Desbloquear el laboratorio", "POST", f"{API}/company-suppliers/<PROVEEDOR>/unblock",
                      body={"version": 3},
                      why=["Desbloquear exige `update`, vuelve a validar la organización y borra el motivo."],
                      show=SUPPLIER_SHOW),
                 call("Inactivar la importadora como proveedor", "POST",
                      f"{API}/company-suppliers/<PROVEEDOR_2>/deactivate", body={"version": 1},
                      why=["Inactivar el proveedor no afecta su relación como cliente."],
                      show=["id", "status", "version"]),
                 call("Listar todos los proveedores", "GET", f"{API}/companies/<EMPRESA>/company-suppliers?status=ALL",
                      why=["`status=ALL` incluye `INACTIVE` y `BLOCKED`; sin `status` solo `ACTIVE`."],
                      show=["items[].internal_code", "items[].status", "total_records"]),
             ]),
    ],
)
