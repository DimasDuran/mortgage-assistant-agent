# Vera

A mortgage application assistant, built as a LangGraph agent. Vera answers
applicant questions about the mortgage process, looks up application status, and
runs exact mortgage calculations (LTV, DTI) through tools.

This is a real project: it uses framework components (LangGraph's prebuilt agent,
ChatAnthropic, tools, checkpointer) rather than hand-rolled equivalents.

## Stack

- Orchestration: LangGraph (`create_react_agent`, checkpointer, HITL)
- Model: Claude via `langchain-anthropic` (`ChatAnthropic`)
- Validation: Pydantic / pydantic-settings
- Packaging: Poetry
- Quality gates: ruff, mypy, pytest

## Layout

```
src/vera/
  core/        # settings (pydantic-settings)
  domain/      # entities and closed types (Pydantic)
  llm/         # chat model construction
  tools/       # tools the agent can call (@tool)
  prompts/     # system prompt
  agents/      # the agent (create_react_agent)
  app.py       # CLI entry points
tests/         # tool unit tests + agent build test
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

## Quality gates

```bash
poetry run ruff check src tests
poetry run mypy
poetry run pytest
```

## Evals (regression testing)

The eval suite runs each case through the agent and scores the reply. Two
evaluation systems are used side by side:

### LLM-as-judge (`src/vera/evals/`)

Single-turn: a question goes in, the reply is graded by a judge model (Claude
Haiku) against a pass/fail criterion. Run locally or on LangSmith:

```bash
python -m vera.evals.run                    # local, prints pass rate
python -m vera.evals.langsmith_eval          # syncs to LangSmith dataset + evaluates
```

### Ragas agent metrics (`src/vera/evals/ragas_*.py`)

Multi-turn: evaluates tool-call quality with structured metrics. Scenarios
define the user messages and what tools the agent *should* call:

| Metric | What it measures |
|---|---|
| `ToolCallAccuracy` | Right tools in the right order? |
| `ToolCallF1` | Precision/recall of tool calls vs expected |
| `TopicAdherence` | Stays on mortgage topics? |
| `AgentGoalAccuracyWithReference` | Achieved the user's goal? |

```bash
python -m vera.evals.ragas_eval              # local run
python -c "from vera.evals.langsmith_eval import run_ragas_eval; run_ragas_eval()"  # logs to LangSmith
```

The Ragas evaluator uses the same agent configuration and can be extended by
adding new scenarios in `src/vera/evals/ragas_cases.py`.

### Live regression gate

A pytest test (`test_ragas_eval.py`) runs the full suite when
`VERA_RUN_LIVE_TESTS=1` is set:

```bash
VERA_RUN_LIVE_TESTS=1 pytest tests/test_ragas_eval.py -v
```

## Roadmap (phases)

1. Agent + tools (this) — done.
2. RAG: a `search_guidelines` tool over a mortgage knowledge base, with citations.
3. Security + human-in-the-loop: domain guardrails, PII handling, indirect-injection
   defense, escalation to a human loan officer via `interrupt`.
4. Evals + regression testing in CI — done (see above).
5. API (FastAPI) and deployment.
