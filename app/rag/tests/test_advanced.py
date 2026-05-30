"""Structured (JSONB) metadata filtering on the retrieval arms — DB-only, no LLM."""
import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Chunk
from app.rag.advanced import _keyword
from app.testing import requires_db

pytestmark = requires_db


@pytest.mark.asyncio
async def test_metadata_containment_filter():
    async with SessionLocal() as s:
        await s.execute(delete(Chunk).where(Chunk.source == "_metatest"))
        s.add_all(
            [
                Chunk(
                    source="_metatest",
                    chunk_index=0,
                    content="connections near max, terminate the stuck backend",
                    embedding=[0.0] * 1536,
                    source_system="gitlab",
                    doc_metadata={"severity": "high", "doc_type": "runbook"},
                    modality="text",
                ),
                Chunk(
                    source="_metatest",
                    chunk_index=1,
                    content="connections near max, informational note only",
                    embedding=[0.0] * 1536,
                    source_system="gitlab",
                    doc_metadata={"severity": "low", "doc_type": "runbook"},
                    modality="text",
                ),
            ]
        )
        await s.commit()

        # filter to high severity → only the first row comes back
        hi = await _keyword(s, "connections near max", 10, None, {"severity": "high"})
        assert [c.chunk_index for c in hi] == [0]

        # no filter → both match the keyword query
        both = await _keyword(s, "connections near max", 10, None, None)
        assert {c.chunk_index for c in both} == {0, 1}

        await s.execute(delete(Chunk).where(Chunk.source == "_metatest"))
        await s.commit()
