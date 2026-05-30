.PHONY: setup up down migrate corpus ingest eval test lint serve

setup:
	python -m pip install -U pip
	pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

migrate:
	alembic upgrade head

corpus:
	python scripts/fetch_corpus.py

ingest: corpus
	python scripts/ingest_all.py

eval:
	python -m eval.run_eval

test:
	pytest -q

lint:
	ruff check .

serve:
	uvicorn app.main:app --reload --port 8000
