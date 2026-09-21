"""expand colombia identification type rules

Revision ID: 0004_expand_co_rules
Revises: 0003_seed_co_rules
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_expand_co_rules"
down_revision: Union[str, Sequence[str], None] = "0003_seed_co_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLOMBIA_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000001"

RULE_IDS = [
    "9d596676-d4c4-5141-b378-2c9eb3c9e4ae",
    "b901502a-4162-58aa-b199-1563bae98636",
    "7c7fd89f-ab95-5c96-afe7-8f5b6b3c9555",
    "3492d46b-f4bd-5578-a1d2-7442ecf2b0e8",
    "7d367f69-71e7-5917-8d67-996fd19931ac",
    "494265ae-ccab-59d0-9116-f12d9c90a740",
    "a2f3b36a-2d8e-591e-bef1-dc9b2516a789",
    "e65078e5-d086-5094-a3d7-3be1ba284b45",
]

PERSON_IDENTIFICATION_TYPES = (
    "'CITIZEN_ID', 'CIVIL_REGISTRY', 'IDENTITY_CARD', "
    "'NATIONAL_ID', 'FOREIGN_CARD', 'FOREIGN_ID', 'PASSPORT', "
    "'TAX_ID', 'TEMPORARY_PROTECTION', 'OTHER'"
)

RULE_IDENTIFICATION_TYPES = (
    "'CITIZEN_ID', 'CIVIL_REGISTRY', 'IDENTITY_CARD', "
    "'NATIONAL_ID', 'FOREIGN_CARD', 'FOREIGN_ID', 'PASSPORT', "
    "'TAX_ID', 'TEMPORARY_PROTECTION', 'REGISTRATION_ID', 'OTHER'"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        type_="check",
    )
    op.create_check_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        f"identification_type IN ({PERSON_IDENTIFICATION_TYPES})",
    )

    op.drop_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        type_="check",
    )
    op.create_check_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        f"identification_type IN ({RULE_IDENTIFICATION_TYPES})",
    )

    rules = [
        {
            "id": RULE_IDS[0],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "CIVIL_REGISTRY",
            "number_pattern": "^[0-9]{10,11}$",
            "number_pattern_description": (
                "El registro civil colombiano debe contener solo numeros "
                "y normalmente corresponde a NUIP de 10 u 11 digitos."
            ),
            "example_value": "1234567890",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[1],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "IDENTITY_CARD",
            "number_pattern": "^[0-9]{10,11}$",
            "number_pattern_description": (
                "La tarjeta de identidad colombiana debe contener solo "
                "numeros y normalmente corresponde a NUIP de 10 u 11 digitos."
            ),
            "example_value": "1234567890",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[2],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "CITIZEN_ID",
            "number_pattern": "^[0-9]{6,10}$",
            "number_pattern_description": (
                "La cedula de ciudadania colombiana debe contener solo "
                "numeros y tener entre 6 y 10 digitos."
            ),
            "example_value": "1234567890",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[3],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "FOREIGN_CARD",
            "number_pattern": "^[A-Z0-9]{3,20}$",
            "number_pattern_description": (
                "La cedula o tarjeta de extranjeria debe contener letras "
                "mayusculas o numeros entre 3 y 20 caracteres."
            ),
            "example_value": "E123456",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[4],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "TEMPORARY_PROTECTION",
            "number_pattern": "^[0-9]{6,12}$",
            "number_pattern_description": (
                "El permiso por proteccion temporal debe contener solo "
                "numeros entre 6 y 12 digitos."
            ),
            "example_value": "1234567",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[5],
            "party_kind": "PERSON",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "OTHER",
            "number_pattern": "^[A-Z0-9-]{1,40}$",
            "number_pattern_description": (
                "Otros documentos de persona deben usar letras mayusculas, "
                "numeros o guion hasta 40 caracteres."
            ),
            "example_value": "DOC-123",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[6],
            "party_kind": "ORGANIZATION",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "REGISTRATION_ID",
            "number_pattern": "^[A-Z0-9-]{3,40}$",
            "number_pattern_description": (
                "El registro mercantil u otro registro de organizacion "
                "debe usar letras mayusculas, numeros o guion."
            ),
            "example_value": "RM-123456",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
        {
            "id": RULE_IDS[7],
            "party_kind": "ORGANIZATION",
            "country_id": COLOMBIA_COUNTRY_ID,
            "identification_type": "OTHER",
            "number_pattern": "^[A-Z0-9-]{1,40}$",
            "number_pattern_description": (
                "Otros documentos de organizacion deben usar letras "
                "mayusculas, numeros o guion hasta 40 caracteres."
            ),
            "example_value": "ORG-123",
            "created_by": SYSTEM_ACTOR_ID,
            "updated_by": SYSTEM_ACTOR_ID,
        },
    ]

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO identification_type_rules (
                id,
                party_kind,
                country_id,
                identification_type,
                number_pattern,
                number_pattern_description,
                example_value,
                is_active,
                created_by,
                updated_by
            )
            VALUES (
                CAST(:id AS uuid),
                :party_kind,
                CAST(:country_id AS uuid),
                :identification_type,
                :number_pattern,
                :number_pattern_description,
                :example_value,
                true,
                CAST(:created_by AS uuid),
                CAST(:updated_by AS uuid)
            )
            ON CONFLICT (
                party_kind,
                country_id,
                identification_type
            )
            WHERE is_active = true
            DO NOTHING
            """
        ),
        rules,
    )


def downgrade() -> None:
    """Downgrade schema."""
    quoted_rule_ids = ", ".join(
        f"'{rule_id}'"
        for rule_id in RULE_IDS
    )

    op.execute(
        sa.text(
            f"""
            DELETE FROM identification_type_rules
            WHERE id IN ({quoted_rule_ids})
            """
        )
    )

    op.drop_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        type_="check",
    )
    op.create_check_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        (
            "identification_type IN ('NATIONAL_ID', 'FOREIGN_ID', "
            "'PASSPORT', 'TAX_ID', 'REGISTRATION_ID', 'OTHER')"
        ),
    )

    op.drop_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        type_="check",
    )
    op.create_check_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        (
            "identification_type IN ('NATIONAL_ID', 'FOREIGN_ID', "
            "'PASSPORT', 'TAX_ID', 'OTHER')"
        ),
    )
