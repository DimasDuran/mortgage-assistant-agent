# Mortgage Assistant Agent

An AI-powered conversational agent that assists borrowers and loan officers
throughout the mortgage origination process. Built with LangGraph, it answers
questions about loan programs and requirements, retrieves application status,
performs precise financial calculations (LTV, DTI), and securely escalates
sensitive matters to human loan officers.

## Problem

The mortgage origination process in the United States is
inefficient, costly, and prone to borrower drop-off. Industry research from
the Mortgage Bankers Association, Freddie Mac, and Fannie Mae documents the
following structural challenges:

**High origination cost per loan.**
According to Freddie Mac and MBA cost studies, the average cost to originate
a single mortgage ranges between $11,100 and $11,800. The primary cost driver
is manual document processing, compliance overhead, and structural inefficiency
in file review — activities that remain largely unautomated at most lenders.

**Borrower abandonment due to digital friction.**
Industry analytics from Cotality and reports covered by HousingWire indicate
that approximately 68% of online loan applications are abandoned before
completion. The leading causes are confusing financial jargon, unclear document
requirements, and a lengthy manual data-entry process that frustrates borrowers
and causes them to ghost the application.

**Urgency to adopt artificial intelligence.**
Fannie Mae projected that over 55% of US mortgage lenders would begin testing
or expanding AI deployments. The market priority is to automate
paper-intensive processes — income verification, bank statement analysis, and
document collection — to reduce the origination cycle and lower operational
costs. This trend was also noted by Forbes, which highlighted that venture
capital is increasingly flowing into AI-driven mortgage origination platforms.

For a broader industry perspective, see
[Forbes — AI Is Rewriting Mortgage Origination, and VCs Are Starting to Notice](https://www.forbes.com/sites/josipamajic/2026/06/18/ai-is-rewriting-mortgage-origination-and-vcs-are-starting-to-note/).

## Solution

This agent addresses four specific friction points in the borrower journey:

### 1. Elimination of endless document exchanges

**Problem:** Borrowers frequently upload incorrect, incomplete, or outdated
documents. Loan officers spend hours chasing the correct files through email
and phone calls.

**Solution:** An AI assistant identifies missing documentation and
automatically follows up with the borrower via email or text message until the
file is complete.

### 2. Form simplification and abandonment reduction

**Problem:** Mortgage forms are lengthy and complex. Borrowers abandon the
process when faced with manual data transcription or questions that do not
apply to their situation.

**Solution:** The platform auto-fills form fields by extracting data from
uploaded documents (W-2s, bank statements). Forms are dynamic — they adapt
questions based on the borrower's profile so only relevant fields are shown.

### 3. Early inconsistency detection before underwriting

**Problem:** Financial inconsistencies, missing documents, or clarification
needs are often discovered weeks later when the file reaches underwriting,
delaying approval and closing.

**Solution:** AI validates each document as it is uploaded. It flags potential
issues — unusual deposits, employment gaps, or inconsistent information —
and requests clarification from the borrower before the file moves forward.

### 4. 24/7 multilingual support

**Problem:** Borrowers have questions about requirements, documentation, or
loan terms outside business hours, stalling the application.

**Solution:** A conversational agent available around the clock answers
mortgage-process questions via messaging channels and email. It interacts
naturally in multiple languages, helping a diverse borrower base complete
applications faster.

## Stack

- **Orchestration:** LangGraph (`create_react_agent`, checkpointer, HITL)
- **Model:** Claude via `langchain-anthropic` (`ChatAnthropic`)
- **Validation:** Pydantic / pydantic-settings
- **API:** FastAPI with multi-tenant auth (Supabase)
- **Observability:** OpenTelemetry (OTLP), LangSmith tracing
- **Packaging:** Poetry
- **Quality:** ruff, mypy, pytest

## Layout

```
src/vera/
  core/        # settings (pydantic-settings), pricing, encryption, telemetry
  domain/      # entities and closed types (Pydantic, aligned to URLA/Form 1003)
  llm/         # chat model construction with prompt caching
  tools/       # tools the agent can call: calculations, application lookup, escalation
  prompts/     # system prompt and LangSmith Prompt Hub integration
  agents/      # the agent (create_react_agent with middleware)
  services/    # application use cases, conversation memory, cost tracking
  repositories/# persistence layer (Supabase or in-memory for dev)
  auth/        # Supabase Auth JWT verification, role-based access, invites
  evals/       # LLM-as-judge and Ragas evaluation suites
  app.py       # CLI entry point
  api.py       # FastAPI application
tests/         # tool unit tests, agent build test, API tests, eval regression
supabase/      # database schema
```

## Setup

```bash
poetry install
cp .env.example .env   # set ANTHROPIC_API_KEY
poetry run pytest
```

## Run a conversation

```bash
poetry run python -m vera.app
```

## API

```bash
poetry run uvicorn vera.api:app --reload --port 8080
curl -X POST localhost:8080/chat \
  -H 'content-type: application/json' \
  -d '{"message":"What is LTV?","thread_id":"t1"}'
```

## Evals

Two complementary evaluation systems:

| System | Scope | Metrics |
|---|---|---|
| LLM-as-judge | Single-turn, pass/fail | Correctness against criteria |
| Ragas | Multi-turn, tool-call quality | ToolCallAccuracy, ToolCallF1, TopicAdherence, AgentGoalAccuracy |

```bash
# LLM-as-judge (local)
python -m vera.evals.run

# Ragas agent metrics (local)
python -m vera.evals.ragas_eval

# LangSmith (both)
python -m vera.evals.langsmith_eval
```

## Quality gates

```bash
poetry run ruff check src tests
poetry run mypy
poetry run pytest
```

## License

MIT
