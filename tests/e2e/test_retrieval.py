"""End-to-end retrieval-quality regression gate: hybrid must not lose to dense.

Needs a real Postgres with the corpus ingested AND a real OpenAI key (it embeds
and judges), so it runs in CI and is skipped on a bare local clone. This is the
one true e2e test — it drives the whole stack — which is why it lives outside the
co-located unit tests under app/.
"""
import pytest

from app.testing import requires_c2, requires_db, requires_openai
from eval.run_eval import evaluate

pytestmark = [requires_c2, requires_db, requires_openai]


@pytest.mark.asyncio
async def test_hybrid_not_worse_than_dense():
    dense = await evaluate("dense")
    hybrid = await evaluate("hybrid")
    assert hybrid["retrieval_hit_rate"] >= dense["retrieval_hit_rate"]
