import logging
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import embed_texts
from app.models import Chunk

log = logging.getLogger(__name__)

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ""}


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def parse_front_matter(text: str) -> tuple[str, dict]:
    """Split optional ``--- ... ---`` YAML-ish front-matter off the top.

    C2 tags every corpus file with ``source_system: <name>``; any other keys
    (title, severity, doc_type, url, …) become the chunk's structured
    ``doc_metadata``. One ``key: value`` per line, no nesting.
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
    # lazy import breaks the ingest <-> multimodal cycle (multimodal reuses
    # chunk_text from this module)
    from app.rag.multimodal import build_units

    p = Path(path)
    if p.suffix.lower() in TEXT_SUFFIXES:
        body, meta = parse_front_matter(load_text(path))
    else:
        body, meta = "", {}  # pdf/image: no front-matter
    source_system = meta.pop("source_system", "unknown")

    units = await build_units(path, body)
    if not units:
        return 0

    embeddings = await embed_texts([u["content"] for u in units])
    source = p.name

    # idempotency: clear prior chunks for this source before re-inserting
    await session.execute(delete(Chunk).where(Chunk.source == source))

    session.add_all(
        [
            Chunk(
                source=source,
                chunk_index=i,
                content=u["content"],
                embedding=e,
                source_system=source_system,
                doc_metadata=meta,  # structured fields, queryable as JSONB
                modality=u["modality"],
            )
            for i, (u, e) in enumerate(zip(units, embeddings))
        ]
    )
    await session.commit()
    log.info(
        "ingested %s (%s): %d units (%s)",
        source,
        source_system,
        len(units),
        ", ".join(sorted({u["modality"] for u in units})),
    )
    return len(units)
