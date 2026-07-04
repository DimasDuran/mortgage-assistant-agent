"""Application lookup tool, backed by the application repository.

Uses a factory so the repository can be injected when building the agent
instead of the tool importing a global singleton.
"""

from langchain_core.tools import BaseTool, tool

from vera.repositories.base import ApplicationRepository


def make_application_status(repo: ApplicationRepository) -> BaseTool:
    """Build the application_status tool bound to the given repository."""

    @tool
    def application_status(application_id: str) -> dict[str, object]:
        """Look up the current status and key details of a mortgage application by ID.

        Use this when the user asks about the status or details of their application
        (e.g. "how is my application APP-1001 doing?").

        Args:
            application_id: the application identifier, e.g. "APP-1001".
        """
        application = repo.get(application_id)
        if application is None:
            return {
                "found": False,
                "message": f"No application found with id {application_id}.",
            }
        subject = (
            application.loan_property.subject_property
            if application.loan_property
            else None
        )
        return {
            "found": True,
            "status": application.status,
            "applicant": (
                application.borrower.full_name if application.borrower else None
            ),
            "loan_amount": subject.loan_amount if subject else None,
            "property_value": subject.property_value if subject else None,
            "occupancy_type": subject.occupancy_type if subject else None,
            "ltv_pct": application.ltv_pct,
            "dti_pct": application.dti_pct,
        }

    return application_status
