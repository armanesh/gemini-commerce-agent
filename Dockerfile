# Builds the React UI and serves it with the FastAPI backend (e.g. on Cloud Run).
FROM node:22-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY commerce_agent ./commerce_agent
COPY api ./api
COPY evals ./evals
RUN pip install --no-cache-dir .
COPY --from=web /web/dist ./web/dist
ENV PORT=8080
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
