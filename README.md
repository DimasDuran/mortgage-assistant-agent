# Mortgage Assistant Agent

An AI-powered conversational agent that assists borrowers and loan officers
throughout the mortgage origination process. Built with LangGraph, it answers
questions about loan programs and requirements, retrieves application status,
performs precise financial calculations (LTV, DTI), and securely escalates
sensitive matters to human loan officers.

## Problem

Applying for a mortgage in the United States involves complex documentation,
eligibility criteria, and financial computations. Lenders like Bank of America
offer detailed guidance at
[https://www.bankofamerica.com/mortgage/home-mortgage/](https://www.bankofamerica.com/mortgage/home-mortgage/),
but borrowers often have repetitive questions about their application status,
loan-to-value ratios, debt-to-income limits, and program requirements.
Meanwhile, loan officers spend a significant portion of their time on routine
inquiries instead of high-value tasks.

This agent automates the information layer: it answers questions grounded in
the lender's knowledge base, computes ratios exactly (never estimating), tracks
the application through its lifecycle, and hands off to a human only when
judgment or approval is required. The result is faster response times for
borrowers and more efficient workflows for lending teams.

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
