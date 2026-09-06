# Backend image: the FastAPI app, managed with uv. The parser (cpsat-logutils) is
# an ordinary dependency and comes from PyPI.
# Build context is the repository root (see docker-compose.yml) so that the
# knowledge base and the example logs can be copied in with the same relative
# layout as in the repository.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /src/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --no-install-project --frozen
COPY backend/app ./app
COPY knowledge /src/knowledge
RUN uv sync --no-dev --frozen

FROM python:3.12-slim-bookworm
WORKDIR /src/backend
COPY --from=builder /src /src
COPY example_logs /example_logs
ENV PATH="/src/backend/.venv/bin:$PATH" EXAMPLE_LOGS_DIR=/example_logs KNOWLEDGE_DIR=/src/knowledge
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
