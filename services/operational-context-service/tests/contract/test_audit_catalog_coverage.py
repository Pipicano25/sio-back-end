"""Cobertura del catálogo de auditoría frente al OpenAPI (feature 016; FR-003; T026).

`specs/016-existing-services-audit/contracts/audit-actions.md`, sección Operational Context: cada
escritura de la API tiene exactamente una acción y viceversa (18).
"""

from __future__ import annotations

from operational_context_service.application import audit_events as audit

CATALOG = {
    ("POST", "/api/v1/companies"): ("CREATE_COMPANY", "Company"),
    ("PUT", "/api/v1/companies/{company_id}"): ("UPDATE_COMPANY", "Company"),
    ("POST", "/api/v1/companies/{company_id}/deactivate"): ("DEACTIVATE_COMPANY", "Company"),
    ("POST", "/api/v1/companies/{company_id}/reactivate"): ("REACTIVATE_COMPANY", "Company"),
    ("POST", "/api/v1/companies/{company_id}/branches"): ("CREATE_BRANCH", "Branch"),
    ("PUT", "/api/v1/branches/{branch_id}"): ("UPDATE_BRANCH", "Branch"),
    ("POST", "/api/v1/branches/{branch_id}/deactivate"): ("DEACTIVATE_BRANCH", "Branch"),
    ("POST", "/api/v1/branches/{branch_id}/reactivate"): ("REACTIVATE_BRANCH", "Branch"),
    ("POST", "/api/v1/companies/{company_id}/application-users"): ("CREATE_APPLICATION_USER", "ApplicationUser"),
    ("PUT", "/api/v1/application-users/{application_user_id}"): ("UPDATE_APPLICATION_USER", "ApplicationUser"),
    ("POST", "/api/v1/application-users/{application_user_id}/deactivate"): ("DEACTIVATE_APPLICATION_USER", "ApplicationUser"),
    ("POST", "/api/v1/application-users/{application_user_id}/reactivate"): ("REACTIVATE_APPLICATION_USER", "ApplicationUser"),
    ("POST", "/api/v1/application-users/{application_user_id}/user-branches"): ("ASSIGN_USER_BRANCH", "UserBranch"),
    ("POST", "/api/v1/user-branches/{user_branch_id}/deactivate"): ("DEACTIVATE_USER_BRANCH", "UserBranch"),
    ("POST", "/api/v1/user-branches/{user_branch_id}/reactivate"): ("REACTIVATE_USER_BRANCH", "UserBranch"),
    ("POST", "/api/v1/companies/{company_id}/advisor-assignments"): ("CREATE_ADVISOR_ASSIGNMENT", "CompanyAdvisorAssignment"),
    ("POST", "/api/v1/advisor-assignments/{assignment_id}/close"): ("CLOSE_ADVISOR_ASSIGNMENT", "CompanyAdvisorAssignment"),
    ("POST", "/api/v1/companies/{company_id}/advisor-assignments/change-primary"): (
        "CHANGE_PRIMARY_ADVISOR_ASSIGNMENT", "CompanyAdvisorAssignment"),
}
READS_BY_POST: set[tuple[str, str]] = set()


def _writes(app) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    } - READS_BY_POST


def test_every_write_has_exactly_one_action(app) -> None:
    assert _writes(app) == set(CATALOG)
    assert len(CATALOG) == 18


def test_catalog_matches_the_service_constants() -> None:
    assert {action for action, _ in CATALOG.values()} == set(audit.ACTIONS)
    assert {entity for _, entity in CATALOG.values()} <= set(audit.ENTITY_TYPES)
