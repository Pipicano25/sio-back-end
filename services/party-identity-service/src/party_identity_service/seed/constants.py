"""Constantes de la carga inicial (Principio XIV, D22 provisional)."""

# Identidad técnica registrada en created_by/updated_by por la carga inicial.
SEED_ACTOR = "system:party-identity-seed"

# Código ISO alfa-3 del país de las reglas iniciales; su UUID se resuelve en
# Geography o se recibe explícitamente, nunca se fija en el código (FR-017).
COUNTRY_ISO3 = "COL"

# Variable de entorno del modo país explícito.
COUNTRY_ID_VARIABLE = "PARTY_IDENTITY_SEED_COUNTRY_ID"

# Reglas colombianas que insertan las migraciones históricas 0006 y 0010, por su llave
# (party_kind, identification_type). La migración 0020 corrige su país con el de este entorno
# (G-017-01); el `seed` las reconoce para no crear copias equivalentes.
HISTORIC_RULE_IDS = {
    ("PERSON", "CIVIL_REGISTRY"): "f1d6549f-7fbb-58bf-8573-b2c629f3d6ae",
    ("PERSON", "IDENTITY_CARD_MODERN"): "09eb08a5-50fc-51bd-a163-9a8493138f02",
    ("PERSON", "IDENTITY_CARD_OLD"): "475acf19-dde0-560d-817f-eec73217fed8",
    ("PERSON", "CITIZEN_ID_MODERN"): "b645336b-b71e-5006-8990-e791a57014d0",
    ("PERSON", "CITIZEN_ID_OLD"): "8628a6ba-2d1c-59fc-a6c9-e8b66452effa",
    ("PERSON", "FOREIGN_CARD"): "a3e75773-1168-5e38-9a21-7354fe7cf38f",
    ("PERSON", "TAX_ID"): "48f7382b-7443-5130-b96e-c19f8f819cc2",
    ("ORGANIZATION", "TAX_ID"): "9c4f89ac-3a77-56e4-9f10-d765c1236df2",
}
