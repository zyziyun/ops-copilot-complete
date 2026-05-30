"""Ingest every data/*.md corpus file (idempotent). Needs DB + OpenAI key."""
import asyncio
from pathlib import Path

from app.db import SessionLocal
from app.rag.ingest import ingest_file


async def main() -> None:
    async with SessionLocal() as session:
        for path in sorted(Path("data").glob("*.md")):
            n = await ingest_file(session, str(path))
            print(f"ingested {path.name}: {n} chunks")


if __name__ == "__main__":
    asyncio.run(main())
