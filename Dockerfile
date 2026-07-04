# Container image for the Vera API.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install poetry

# Install dependencies first (better layer caching).
COPY pyproject.toml poetry.lock README.md ./
COPY src/ ./src/
RUN poetry install --only main

EXPOSE 8080

# Secrets (ANTHROPIC_API_KEY, LANGSMITH_*, VOYAGE_API_KEY, PINECONE_API_KEY,
# VERA_API_KEY) are provided as environment variables by the platform at runtime.
CMD ["uvicorn", "vera.api:app", "--host", "0.0.0.0", "--port", "8080"]
