# --- builder: build a wheel from pyproject and install it (+ deps) ---
FROM python:3.12-slim AS builder
WORKDIR /src
COPY pyproject.toml ./
COPY app/ ./app/
COPY mcp_servers/ ./mcp_servers/
RUN pip install --user --no-cache-dir .

# --- runtime: copy the installed packages + migration assets only ---
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY data/ ./data/
COPY scripts/ ./scripts/
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "2", "-b", "0.0.0.0:8000", \
     "--timeout", "120"]
