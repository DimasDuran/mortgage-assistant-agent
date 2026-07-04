# Deploying Vera

The API is a container. Build it once and run it on any container host. Secrets are
provided as environment variables at runtime, never baked into the image.

## Run locally

```bash
poetry run uvicorn vera.api:app --reload --port 8080
# health check
curl localhost:8080/health
# chat (set VERA_API_KEY to require the header in production)
curl -X POST localhost:8080/chat -H 'content-type: application/json' \
  -d '{"message":"What is LTV?","thread_id":"t1"}'
```

## Build the image

```bash
docker build -t vera-api .
docker run -p 8080:8080 --env-file .env vera-api
```

## Required environment variables (set in the platform, not the image)

- `ANTHROPIC_API_KEY` - model
- `VOYAGE_API_KEY`, `PINECONE_API_KEY` - retrieval
- `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=vera` - observability
- `VERA_API_KEY` - API auth (required in production)

## Deploy (AWS + the MLOps guide)

Recommended path (see `GUIA-MLOPS-DESPLIEGUE-AWS-VERCEL.md` in the roadmap repo):

1. Push the image to a registry (GitLab Container Registry or AWS ECR).
2. Run it on AWS App Runner (simplest) or ECS Fargate, with the env vars above
   set as platform secrets (AWS Secrets Manager).
3. Front it with HTTPS and a domain. A Vercel frontend (if any) calls this API;
   the API keeps all keys server-side.

This step needs your cloud account and credentials, so it is run by you (or a CI
job with deploy credentials), not from this repo by default. The knowledge base
must be ingested once (`python -m vera.rag.ingest`) against the production
Pinecone index before serving.
