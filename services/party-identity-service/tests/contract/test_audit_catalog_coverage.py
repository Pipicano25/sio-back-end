"""Cobertura del catálogo de auditoría frente al OpenAPI (feature 016; FR-003; T044).

`specs/016-existing-services-audit/contracts/audit-actions.md`, sección Party Identity (32).
"""

from __future__ import annotations

from party_identity_service.application import audit_events as audit

P = "/api/v1/person-identities/{person_identity_id}"
O = "/api/v1/organization-identities/{organization_identity_id}"
R = "/api/v1/identification-type-rules"
CATALOG = {
    ("POST", "/api/v1/person-identities"): ("CREATE_PERSON_IDENTITY", "PersonIdentity"),
    ("PUT", P): ("UPDATE_PERSON_IDENTITY", "PersonIdentity"),
    ("POST", f"{P}/deactivate"): ("DEACTIVATE_PERSON_IDENTITY", "PersonIdentity"),
    ("POST", f"{P}/reactivate"): ("REACTIVATE_PERSON_IDENTITY", "PersonIdentity"),
    ("POST", "/api/v1/organization-identities"): ("CREATE_ORGANIZATION_IDENTITY", "OrganizationIdentity"),
    ("PUT", O): ("UPDATE_ORGANIZATION_IDENTITY", "OrganizationIdentity"),
    ("POST", f"{O}/deactivate"): ("DEACTIVATE_ORGANIZATION_IDENTITY", "OrganizationIdentity"),
    ("POST", f"{O}/reactivate"): ("REACTIVATE_ORGANIZATION_IDENTITY", "OrganizationIdentity"),
    ("POST", R): ("CREATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule"),
    ("PUT", f"{R}/{{rule_id}}"): ("UPDATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule"),
    ("POST", f"{R}/{{rule_id}}/versions"): ("CREATE_IDENTIFICATION_TYPE_RULE_VERSION", "IdentificationTypeRule"),
    ("POST", f"{R}/{{rule_id}}/deactivate"): ("DEACTIVATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule"),
    ("POST", f"{P}/contact-profile"): ("REGISTER_PERSON_CONTACT_PROFILE", "PersonContactProfile"),
    ("POST", f"{P}/contact-profile:close"): ("CLOSE_PERSON_CONTACT_PROFILE", "PersonContactProfile"),
    ("POST", f"{O}/contact-profile"): ("REGISTER_ORGANIZATION_CONTACT_PROFILE", "OrganizationContactProfile"),
    ("POST", f"{O}/contact-profile:close"): ("CLOSE_ORGANIZATION_CONTACT_PROFILE", "OrganizationContactProfile"),
    ("POST", f"{O}/contact-persons"): ("CREATE_ORGANIZATION_CONTACT_PERSON", "OrganizationContactPerson"),
    ("PUT", "/api/v1/organization-contact-persons/{contact_id}"): ("UPDATE_ORGANIZATION_CONTACT_PERSON", "OrganizationContactPerson"),
    ("POST", "/api/v1/organization-contact-persons/{contact_id}:set-primary"): (
        "SET_PRIMARY_ORGANIZATION_CONTACT_PERSON", "OrganizationContactPerson"),
    ("POST", "/api/v1/organization-contact-persons/{contact_id}:deactivate"): (
        "DEACTIVATE_ORGANIZATION_CONTACT_PERSON", "OrganizationContactPerson"),
    ("POST", "/api/v1/organization-contact-persons/{contact_id}:reactivate"): (
        "REACTIVATE_ORGANIZATION_CONTACT_PERSON", "OrganizationContactPerson"),
    ("POST", "/api/v1/global-business-sectors"): ("CREATE_GLOBAL_BUSINESS_SECTOR", "GlobalBusinessSector"),
    ("PUT", "/api/v1/global-business-sectors/{sector_id}"): ("UPDATE_GLOBAL_BUSINESS_SECTOR", "GlobalBusinessSector"),
    ("POST", "/api/v1/global-business-sectors/{sector_id}:deactivate"): ("DEACTIVATE_GLOBAL_BUSINESS_SECTOR", "GlobalBusinessSector"),
    ("POST", "/api/v1/global-business-sectors/{sector_id}:reactivate"): ("REACTIVATE_GLOBAL_BUSINESS_SECTOR", "GlobalBusinessSector"),
    ("POST", f"{O}/business-sectors"): ("ASSIGN_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector"),
    ("POST", "/api/v1/organization-business-sectors/{assignment_id}:set-primary"): (
        "SET_PRIMARY_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector"),
    ("POST", "/api/v1/organization-business-sectors/{assignment_id}:close"): (
        "CLOSE_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector"),
    ("POST", f"{O}/legal-representatives"): ("CREATE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative"),
    ("POST", f"{O}/legal-representatives:set-primary"): (
        "SET_PRIMARY_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative"),
    ("PUT", "/api/v1/organization-legal-representatives/{representative_id}"): (
        "UPDATE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative"),
    ("POST", "/api/v1/organization-legal-representatives/{representative_id}:close"): (
        "CLOSE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative"),
}


def _writes(app) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    }


def test_every_write_has_exactly_one_action(app) -> None:
    assert _writes(app) == set(CATALOG)
    assert len(CATALOG) == 32


def test_catalog_matches_the_service_constants() -> None:
    assert {action for action, _ in CATALOG.values()} == set(audit.ACTIONS)
    assert {entity for _, entity in CATALOG.values()} == set(audit.ENTITY_TYPES)
