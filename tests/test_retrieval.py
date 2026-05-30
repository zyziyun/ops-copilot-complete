"""Retrieval-quality regression gate: hybrid must not lose to dense.

Needs a real Postgres with the corpus ingested AND a real OpenAI key (it embeds
and judges), so it runs in CI and is skipped on a bare local clone.
"""
import pytest

from eval.run_eval import evaluate
from tests.helpers import requires_c2, requires_db, requires_openai

pytestmark = requires_c2  # hybrid + evaluate land in C2


@requires_db
@requires_openai
@pytest.mark.asyncio
async def test_hybrid_not_worse_than_dense():
    dense = await evaluate("dense")
    hybrid = await evaluate("hybrid")
    assert hybrid["retrieval_hit_rate"] >= dense["retrieval_hit_rate"]
