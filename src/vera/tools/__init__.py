"""Tools the agent can call. Add a capability = add a @tool and list it here.

Tools are built via get_tools() so dependencies (like the application repo)
can be injected at agent-build time instead of imported as global singletons.
"""

from langchain_core.tools import BaseTool

from vera.repositories import get_application_repository
from vera.repositories.base import ApplicationRepository
from vera.tools.applications import make_application_status
from vera.tools.calculations import calculate_dti, calculate_ltv
from vera.tools.escalation import escalate_to_loan_officer


def get_tools(repo: ApplicationRepository | None = None) -> list[BaseTool]:
    """Return the tool list, optionally with a custom repo injected.

    When called from the CLI (no repo), the default singleton is used.
    When called from the HTTP API, the request-scoped repo is injected so
    tenant isolation is maintained (the repo is already scoped by org).
    """
    repo = repo or get_application_repository()
    return [
        calculate_ltv,
        calculate_dti,
        make_application_status(repo),
        escalate_to_loan_officer,
    ]
