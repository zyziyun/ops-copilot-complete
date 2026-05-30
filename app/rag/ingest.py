import logging
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import embed_texts
from app.models import Chunk

log = logging.getLogger(__name__)


def load_text(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # pip install pypdf if you need PDFs

        reader = PdfReader(str(p))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return p.read_text(encoding="utf-8")


def parse_front_matter(text: str) -> tuple[str, dict]:
    """Split optional ``--- ... ---`` YAML-ish front-matter off the top.

    C2 tags every corpus file with ``source_system: <name>`` so retrieval can
    filter and attribute by origin. We keep the parser tiny on purpose: one
    ``key: value`` per line, no nesting.
    """
    meta: dict[str, str] = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip()
            for line in block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip()
            text = text[end + 4 :].lstrip("\n")
    return text, meta


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return [c for c in chunks if c.strip()]


async def ingest_file(session: AsyncSession, path: str) -> int:
    raw = load_text(path)
    body, meta = parse_front_matter(raw)
    source_system = meta.get("source_system", "unknown")

    chunks = chunk_text(body)
    if not chunks:
        return 0

    embeddings = await embed_texts(chunks)
    source = Path(path).name

    # idempotency: clear prior chunks for this source before re-inserting
    await session.execute(delete(Chunk).where(Chunk.source == source))

    session.add_all(
        [
            Chunk(
                source=source,
                chunk_index=i,
                content=c,
                embedding=e,
                source_system=source_system,
            )
            for i, (c, e) in enumerate(zip(chunks, embeddings))
        ]
    )
    await session.commit()
    log.info("ingested %s (%s): %d chunks", source, source_system, len(chunks))
    return len(chunks)
