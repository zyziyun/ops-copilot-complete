# Thin task runner over uv (the package/dependency tool). Dependencies live in
# pyproject.toml; `uv sync` builds the venv and installs them.
.PHONY: setup up full down migrate corpus ingest eval test lint serve mcp-ops mcp-search inspect

setup:
	uv sync --extra dev

up:
	docker compose up -d # Postgres only (local dev)

full:
	docker compose --profile full up --build # db + migrate + api + both MCP servers

down:
	docker compose down

migrate:
	uv run alembic upgrade head

corpus:
	uv run python scripts/fetch_corpus.py

ingest: corpus
	uv run python scripts/ingest_all.py

eval:
	uv run python -m eval.run_eval

test:
	uv run pytest -q

lint:
	uv run ruff check .

serve:
	uv run uvicorn app.main:app --reload --port 8000

mcp-ops:
	uv run python -m mcp_servers.ops_server # http://localhost:8001/mcp

mcp-search:
	uv run python -m mcp_servers.search_server # http://localhost:8002/mcp

inspect:
	# MCP Inspector UI — connect it to http://localhost:8001/mcp or :8002/mcp
	npx @modelcontextprotocol/inspector
