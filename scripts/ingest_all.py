"""Ingest every data/*.md corpus file (idempotent). Needs DB + OpenAI key."""
import asyncio
import sys
from pathlib import Path

# allow running as `python scripts/ingest_all.py` (not just `python -m ...`):
# put the repo root on sys.path so the `app` package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.rag.ingest import ingest_file  # noqa: E402


async def main() -> None:
    async with SessionLocal() as session:
        for path in sorted(Path("data").glob("*.md")):
            n = await ingest_file(session, str(path))
            print(f"ingested {path.name}: {n} chunks")


if __name__ == "__main__":
    asyncio.run(main())
