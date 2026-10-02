"""Ejercicio 8 de docs/ejemplo/: representantes legales (Fase B; FR-070–FR-078, DS-06, DS-13)."""

from tests.examples.spec_common import API, call, get_colombia, step

REP_SHOW = ["id", "person_identity_id", "representative_type", "is_primary", "is_active",
            "source_document_reference", "version"]

ORGANIZATION = {
    "country_id": "<PAIS_CO>",
    "identification_type": "NIT",
    "identification_number": "900000008-8",
    "legal_name": "INVERSIONES REPRESENTACION FICTICIA S.A.S.",
}


def _person(number: str, first_name: str) -> dict:
    return {
        "identification_country_id": "<PAIS_CO>",
        "identification_type": "CC",
        "identification_number": number,
        "first_name": first_name,
        "last_name": "REPRESENTANTE",
        "second_last_name": "FICTICIO",
        "birth_date": "1975-01-15",
    }


EX8 = dict(
    folder="8-representantes-legales",
    title="Ejercicio 8 — Representantes legales: PRIMARY único, set-primary y cierre",
    focus=(
        "Establecer el **primer** representante `PRIMARY` con `set-primary`, ver el `409` al registrar otro `PRIMARY` "
        "por el alta ordinaria, **sustituirlo** con `set-primary` (cierra el anterior y crea el nuevo), registrar un "
        "suplente con su **referencia documental** y cerrarlo. Es un dato sensible: `compras.test` recibe `403`."
    ),
    data=[
        ("Organización", "INVERSIONES REPRESENTACION FICTICIA S.A.S. — NIT `900000008-8` (**ficticios**)"),
        ("Representantes", "`CC 1000000081` y `CC 1000000082` (**ficticios**)"),
        ("Referencia documental", "\"Acta 001 de 2026 (ficticia)\": solo texto, no se guarda el documento"),
    ],
    interpretation=[
        ("PRIMARY único", "Como máximo un `PRIMARY` vigente por organización; `ALTERNATE` y `OTHER` pueden ser varios."),
        ("set-primary", "Establece el primero o sustituye el vigente en una operación; nunca dos `PUT`."),
        ("Vigencia", "`[valid_from, valid_to)`: cerrar antes de que empiece la vigencia deja `valid_to = valid_from`."),
        ("Datos sensibles", "Se leen con `organization_legal_representatives:read`, que solo tienen administradores y "
         "supervisores."),
    ],
    order_rules=[
        ("Identidades primero", "Organización y personas deben existir y estar `ACTIVE`."),
        ("PRIMARY antes de sustituirlo", "La sustitución envía `current_primary_version` del `PRIMARY` vigente."),
    ],
    steps=[
        step("01-consultar-pais.md", "Consultar el país", "Obtener `<PAIS_CO>`.", [get_colombia()]),
        step(
            "02-registrar-identidades.md", "Registrar la organización y las personas", "Crear las identidades.",
            [
                call("Registrar la organización", "POST", f"{API}/organization-identities", body=ORGANIZATION,
                     save={"ORG_INV": "id"}, show=["id", "legal_name", "status"]),
                call("Registrar la primera persona", "POST", f"{API}/person-identities",
                     body=_person("1000000081", "JORGE"), save={"PERSONA_JORGE": "id"},
                     show=["id", "first_name", "status"]),
                call("Registrar la segunda persona", "POST", f"{API}/person-identities",
                     body=_person("1000000082", "ELENA"), save={"PERSONA_ELENA": "id"},
                     show=["id", "first_name", "status"]),
            ],
        ),
        step(
            "03-establecer-primary.md", "Establecer y sustituir el PRIMARY", "Usar set-primary y ver el conflicto.",
            [
                call("Establecer el primer PRIMARY", "POST",
                     f"{API}/organization-identities/<ORG_INV>/legal-representatives:set-primary",
                     body={"person_identity_id": "<PERSONA_JORGE>", "position": "Gerente general"},
                     why=["No hay `PRIMARY` vigente: se crea el primero (no se envía `current_primary_version`)."],
                     expect=201, save={"REP_JORGE": "id"}, show=REP_SHOW),
                call("Intentar registrar otro PRIMARY por el alta ordinaria (rechazado)", "POST",
                     f"{API}/organization-identities/<ORG_INV>/legal-representatives",
                     body={"person_identity_id": "<PERSONA_ELENA>", "representative_type": "PRIMARY"},
                     why=["Ya hay uno: `409 PRIMARY_REPRESENTATIVE_CONFLICT`."], expect=409, show=["status", "code"]),
                call("Sustituir el PRIMARY", "POST",
                     f"{API}/organization-identities/<ORG_INV>/legal-representatives:set-primary",
                     body={"person_identity_id": "<PERSONA_ELENA>", "position": "Gerente general",
                           "current_primary_version": 1,
                           "source_document_reference": "Acta 001 de 2026 (ficticia)"},
                     why=["Cierra la relación de JORGE (`valid_to`) y crea la de ELENA en la misma operación."],
                     expect=201, save={"REP_ELENA": "id"}, show=REP_SHOW),
            ],
        ),
        step(
            "04-suplente-y-cierre.md", "Suplente, historial y cierre", "Registrar un suplente y cerrarlo.",
            [
                call("Registrar a JORGE como suplente", "POST",
                     f"{API}/organization-identities/<ORG_INV>/legal-representatives",
                     body={"person_identity_id": "<PERSONA_JORGE>", "representative_type": "ALTERNATE",
                           "source_document_reference": "   "},
                     why=["Su relación anterior está cerrada: se crea una fila nueva (las cerradas no se reactivan).",
                          "Una referencia documental de solo espacios se guarda como `null`."],
                     save={"REP_JORGE_SUPLENTE": "id"}, show=REP_SHOW),
                call("Cerrar la relación de suplente", "POST",
                     f"{API}/organization-legal-representatives/<REP_JORGE_SUPLENTE>:close", body={"version": 1},
                     why=["Exige `delete`; no borra."], show=REP_SHOW),
                call("Consultar el historial", "GET",
                     f"{API}/organization-identities/<ORG_INV>/legal-representatives?state=all",
                     why=["`state=active` (por defecto), `closed` o `all`."], show=["total_records"]),
            ],
        ),
    ],
)
