"""HTTP API for Vera (FastAPI).

Exposes the agent over HTTP: a chat endpoint, a resume endpoint for the
human-in-the-loop approval flow, a health check, and the application CRUD.
The chat endpoints use an API key header (disabled if VERA_API_KEY is unset).
The application endpoints use Supabase Auth JWTs with role- and case-scoped
access (disabled if SUPABASE_JWT_SECRET is unset, for local development).
"""

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.types import Command
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from vera.agents.agent import build_agent
from vera.app import _build_messages, _get_memory, _maybe_summarize, _reply
from vera.auth.dependencies import (
    UserDep,
    can_access_organization,
    require_org_admin,
    require_staff,
    require_super_admin,
)
from vera.auth.invites import Inviter, build_supabase_inviter
from vera.auth.tokens import AuthenticatedUser
from vera.core.config import get_settings
from vera.core.pricing import calculate_cost
from vera.core.telemetry import instrument_fastapi, setup_telemetry
from vera.domain.enums import ApplicationStatus, UserRole
from vera.domain.models import (
    Application,
    BorrowerInformation,
    Declarations,
    FinancialProfile,
    Income,
    LoanAndProperty,
    Organization,
)
from vera.domain.status import InvalidStatusTransition
from vera.llm.model import build_model
from vera.prompts.system import SYSTEM_PROMPT
from vera.repositories import get_application_repository
from vera.repositories.base import ApplicationRepository, PaginatedResult
from vera.repositories.organizations import (
    OrganizationRepository,
    get_organization_repository,
)
from vera.services import applications as application_service
from vera.services import organizations as organization_service
from vera.services.applications import ApplicationNotFoundError
from vera.services.cost_tracker import ThreadCostTracker, extract_usage_from_result
from vera.services.organizations import OrganizationNotFoundError

# Load .env so model/observability keys are available when served.
load_dotenv()

# Show OTel initialisation banner in server output.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", force=True)

settings = get_settings()

_limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_per_minute > 0,
)

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    setup_telemetry()
    instrument_fastapi(application)
    yield


app = FastAPI(
    title="Vera",
    description="Mortgage assistant agent API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = _limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

_agent: Runnable | None = None
_thread_trackers: dict[str, ThreadCostTracker] = {}


def get_agent() -> Runnable:
    """Build the agent once and reuse it (overridable in tests)."""
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def _get_tracker(thread_id: str, model_name: str | None = None) -> ThreadCostTracker:
    if thread_id not in _thread_trackers:
        _thread_trackers[thread_id] = ThreadCostTracker(
            model=model_name or settings.model,
        )
    return _thread_trackers[thread_id]


def _check_budget(thread_id: str, usage: dict) -> None:
    budget = settings.max_budget_per_session
    if budget is None:
        return
    tracker = _get_tracker(thread_id)
    current = tracker.accumulated_cost
    expected = current + calculate_cost(settings.model, **usage)
    if expected > budget:
        import warnings
        warnings.warn(
            f"Thread {thread_id} would exceed budget ${budget:.4f} "
            f"(projected ${expected:.4f})",
            stacklevel=2,
        )


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Reject requests without the configured API key. No-op if none is set."""
    expected = get_settings().api_key
    if expected is None:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


AgentDep = Annotated[Runnable, Depends(get_agent)]


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class ResumeRequest(BaseModel):
    thread_id: str
    approve: bool
    message: str | None = None


class ChatResponse(BaseModel):
    reply: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_tokens: int | None = None
    cache_read_tokens: int | None = None
    cost: float | None = None
    session_cost: float | None = None


def _build_chat_response(
    result: dict[str, Any],
    thread_id: str,
) -> ChatResponse:
    reply = _reply(result)
    usage = extract_usage_from_result(result)
    usage_cost = calculate_cost(settings.model, **usage)
    _check_budget(thread_id, usage)
    tracker = _get_tracker(thread_id)
    tracker.add_turn(**usage)
    return ChatResponse(
        reply=reply,
        input_tokens=usage["input_tokens"] or None,
        output_tokens=usage["output_tokens"] or None,
        cache_creation_tokens=usage["cache_creation_input_tokens"] or None,
        cache_read_tokens=usage["cache_read_input_tokens"] or None,
        cost=round(usage_cost, 6),
        session_cost=tracker.accumulated_cost,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_RATE_LIMIT = f"{settings.rate_limit_per_minute}/minute"


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
@_limiter.limit(_RATE_LIMIT)
async def chat_endpoint(
    request: Request, body: ChatRequest, agent: AgentDep
) -> ChatResponse:
    """Send a message to the agent. May return an approval-required reply (HITL)."""
    memory = _get_memory()
    config: RunnableConfig = {"configurable": {"thread_id": body.thread_id}}
    payload = {"messages": _build_messages(body.message, body.thread_id, memory)}
    result: Any = await agent.ainvoke(payload, config)
    _maybe_summarize(agent, config, result, body.thread_id, memory)
    return _build_chat_response(result, body.thread_id)


@app.post(
    "/chat/resume",
    response_model=ChatResponse,
    dependencies=[Depends(require_api_key)],
)
@_limiter.limit(_RATE_LIMIT)
async def resume_endpoint(
    request: Request, body: ResumeRequest, agent: AgentDep
) -> ChatResponse:
    """Resume a conversation paused for human approval (human-in-the-loop)."""
    decision: dict[str, Any] = (
        {"type": "approve"}
        if body.approve
        else {"type": "reject", "message": body.message or "Rejected by reviewer."}
    )
    config: RunnableConfig = {"configurable": {"thread_id": body.thread_id}}
    result: Any = await agent.ainvoke(Command(resume={"decisions": [decision]}), config)
    return _build_chat_response(result, body.thread_id)


class BudgetCheckRequest(BaseModel):
    message: str
    thread_id: str


@app.post("/chat/budget-check", dependencies=[Depends(require_api_key)])
@_limiter.limit(_RATE_LIMIT)
async def budget_check(
    request: Request,
    body: BudgetCheckRequest,
) -> dict[str, Any]:
    """Estimate input tokens & cost BEFORE sending, without triggering the agent."""
    local_model = build_model(settings)
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    if body.message:
        messages.append(HumanMessage(content=body.message))
    try:
        count = local_model.get_num_tokens_from_messages(messages)
        budget = settings.max_tokens_per_turn
        estimated_cost = calculate_cost(
            settings.model,
            input_tokens=count,
            output_tokens=settings.max_tokens,
        )
        return {
            "estimated_input_tokens": count,
            "estimated_output_tokens": settings.max_tokens,
            "estimated_cost": round(estimated_cost, 6),
            "over_budget": budget is not None and count > budget,
            "budget": budget,
        }
    except Exception as exc:
        return {"error": f"Budget check failed: {exc}"}


# --- Multi-tenant applications and organizations (Supabase Auth) ---


def get_repo() -> ApplicationRepository:
    return get_application_repository()


def get_org_repo() -> OrganizationRepository:
    return get_organization_repository()


RepoDep = Annotated[ApplicationRepository, Depends(get_repo)]
OrgRepoDep = Annotated[OrganizationRepository, Depends(get_org_repo)]

StaffDep = Annotated[AuthenticatedUser, Depends(require_staff)]
OrgAdminDep = Annotated[AuthenticatedUser, Depends(require_org_admin)]
SuperAdminDep = Annotated[AuthenticatedUser, Depends(require_super_admin)]


def get_inviter() -> Inviter:
    """Build the Supabase-backed inviter (overridable in tests)."""
    return build_supabase_inviter(get_settings())


InviterDep = Annotated[Inviter, Depends(get_inviter)]


def get_accessible_application(
    application_id: str, repo: RepoDep, user: UserDep
) -> Application:
    """Load a case enforcing tenant and role scope. 404 if missing, 403 if denied."""
    application = application_service.get_application(repo, application_id)
    if application is None:
        raise ApplicationNotFoundError(application_id)
    if not can_access_organization(user, application.organization_id or ""):
        raise HTTPException(status_code=403, detail="No access to this application.")
    is_borrower = user.role in {"borrower", "co_borrower"}
    if is_borrower and user.application_id != application_id:
        raise HTTPException(status_code=403, detail="No access to this application.")
    return application


AppDep = Annotated[Application, Depends(get_accessible_application)]


@app.exception_handler(ApplicationNotFoundError)
async def _application_not_found(
    request: Request, exc: ApplicationNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404, content={"detail": f"Application {exc} not found."}
    )


@app.exception_handler(OrganizationNotFoundError)
async def _organization_not_found(
    request: Request, exc: OrganizationNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404, content={"detail": f"Organization {exc} not found."}
    )


@app.exception_handler(InvalidStatusTransition)
async def _invalid_status_transition(
    request: Request, exc: InvalidStatusTransition
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


class CreateOrganizationRequest(BaseModel):
    name: str


class CreateApplicationRequest(BaseModel):
    name: str | None = None
    # Only super_admin (who has no fixed org) needs to specify this.
    organization_id: str | None = None


class StatusUpdate(BaseModel):
    status: ApplicationStatus


class InviteRequest(BaseModel):
    email: str
    role: UserRole = "borrower"


# --- Organizations (platform level: super_admin manages tenants) ---


@app.post("/organizations", response_model=Organization)
def create_organization(
    request: CreateOrganizationRequest, org_repo: OrgRepoDep, _: SuperAdminDep
) -> Organization:
    """Create a new tenant. Platform super_admin only."""
    return organization_service.create_organization(org_repo, request.name)


@app.get("/organizations", response_model=list[Organization])
def list_organizations(org_repo: OrgRepoDep, _: SuperAdminDep) -> list[Organization]:
    """List all tenants. Platform super_admin only."""
    return organization_service.list_organizations(org_repo)


@app.get("/organizations/{organization_id}", response_model=Organization)
def get_organization(
    organization_id: str, org_repo: OrgRepoDep, user: UserDep
) -> Organization:
    if not can_access_organization(user, organization_id):
        raise HTTPException(status_code=403, detail="No access to this organization.")
    organization = organization_service.get_organization(org_repo, organization_id)
    if organization is None:
        raise OrganizationNotFoundError(organization_id)
    return organization


@app.post("/organizations/{organization_id}/invite", status_code=202)
def invite_staff(
    organization_id: str,
    body: InviteRequest,
    org_repo: OrgRepoDep,
    inviter: InviterDep,
    user: OrgAdminDep,
) -> dict[str, str]:
    """Invite a staff member (admin/loan_officer/operations) into an org."""
    if not can_access_organization(user, organization_id):
        raise HTTPException(status_code=403, detail="No access to this organization.")
    if organization_service.get_organization(org_repo, organization_id) is None:
        raise OrganizationNotFoundError(organization_id)
    if body.role not in {"admin", "loan_officer", "operations"}:
        raise HTTPException(
            status_code=422,
            detail="Staff role must be admin, loan_officer, or operations.",
        )
    inviter(body.email, body.role, organization_id, None)
    return {"detail": f"Invitation sent to {body.email}."}


# --- Applications (tenant level: staff manage cases, borrowers fill them) ---


@app.post("/applications", response_model=Application)
def create_application(
    request: CreateApplicationRequest, repo: RepoDep, user: StaffDep
) -> Application:
    """Create a new case (draft) in the caller's organization. Staff only."""
    org_id = request.organization_id or user.organization_id
    if not org_id:
        raise HTTPException(status_code=422, detail="organization_id is required.")
    if not can_access_organization(user, org_id):
        raise HTTPException(status_code=403, detail="No access to this organization.")
    return application_service.create_application(repo, org_id, request.name)


@app.get("/applications", response_model=PaginatedResult)
def list_applications(
    repo: RepoDep,
    user: StaffDep,
    limit: int | None = None,
    offset: int = 0,
) -> PaginatedResult:
    """List cases in the caller's org (all orgs for super_admin). Staff only."""
    org_id = None if user.role == "super_admin" else user.organization_id
    return application_service.list_applications(
        repo, org_id, limit=limit, offset=offset
    )


@app.post("/applications/{application_id}/invite", status_code=202)
def invite_to_application(
    body: InviteRequest,
    inviter: InviterDep,
    application: AppDep,
    _: StaffDep,
) -> dict[str, str]:
    """Invite a borrower/co_borrower to a case (invite-only account). Staff only."""
    if body.role not in {"borrower", "co_borrower"}:
        raise HTTPException(
            status_code=422, detail="Case role must be borrower or co_borrower."
        )
    inviter(body.email, body.role, application.organization_id or "", application.id)
    return {"detail": f"Invitation sent to {body.email}."}


@app.get("/applications/{application_id}", response_model=Application)
def get_application(application: AppDep) -> Application:
    return application


@app.put("/applications/{application_id}/borrower", response_model=Application)
def put_borrower(
    borrower: BorrowerInformation, repo: RepoDep, application: AppDep
) -> Application:
    return application_service.update_borrower(repo, application.id, borrower)


@app.put("/applications/{application_id}/income", response_model=Application)
def put_income(income: Income, repo: RepoDep, application: AppDep) -> Application:
    return application_service.update_income(repo, application.id, income)


@app.put("/applications/{application_id}/financial-profile", response_model=Application)
def put_financial_profile(
    profile: FinancialProfile, repo: RepoDep, application: AppDep
) -> Application:
    return application_service.update_financial_profile(repo, application.id, profile)


@app.put("/applications/{application_id}/loan-property", response_model=Application)
def put_loan_property(
    loan_property: LoanAndProperty, repo: RepoDep, application: AppDep
) -> Application:
    return application_service.update_loan_property(repo, application.id, loan_property)


@app.put("/applications/{application_id}/declarations", response_model=Application)
def put_declarations(
    declarations: Declarations, repo: RepoDep, application: AppDep
) -> Application:
    return application_service.update_declarations(repo, application.id, declarations)


@app.patch("/applications/{application_id}/status", response_model=Application)
def patch_status(body: StatusUpdate, repo: RepoDep, application: AppDep) -> Application:
    return application_service.set_status(repo, application.id, body.status)
