"""Seed the configured repositories with demo data.

Useful to populate fresh Supabase tables:  python -m vera.repositories.seed
"""

from dotenv import load_dotenv

from vera.repositories import get_application_repository
from vera.repositories.memory import demo_applications
from vera.repositories.organizations import (
    demo_organizations,
    get_organization_repository,
)


def main() -> None:
    load_dotenv()

    org_repository = get_organization_repository()
    organizations = demo_organizations()
    for organization in organizations.values():
        org_repository.upsert(organization)

    repository = get_application_repository()
    applications = demo_applications()
    for application in applications.values():
        repository.upsert(application)

    print(
        f"Seeded {len(organizations)} organizations and "
        f"{len(applications)} applications into the repositories."
    )


if __name__ == "__main__":
    main()
