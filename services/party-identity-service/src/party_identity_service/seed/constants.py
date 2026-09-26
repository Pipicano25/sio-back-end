"""Constantes de la carga inicial (Principio XIV, D22 provisional)."""

# Identidad técnica registrada en created_by/updated_by por la carga inicial.
SEED_ACTOR = "system:party-identity-seed"

# Código ISO alfa-3 del país de las reglas iniciales; su UUID se resuelve en
# Geography o se recibe explícitamente, nunca se fija en el código (FR-017).
COUNTRY_ISO3 = "COL"

# Variable de entorno del modo país explícito.
COUNTRY_ID_VARIABLE = "PARTY_IDENTITY_SEED_COUNTRY_ID"
