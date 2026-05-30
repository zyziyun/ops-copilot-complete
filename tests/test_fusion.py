from types import SimpleNamespace as NS

from app.rag.fusion import rrf_merge
from tests.helpers import requires_c2

pytestmark = requires_c2  # skip until C2's rrf_merge is implemented


def test_rrf_merge_orders_by_fused_rank():
    # list A ranks: 1, 2, 3   list B ranks: 3, 2, 4
    a = [NS(id=1), NS(id=2), NS(id=3)]
    b = [NS(id=3), NS(id=2), NS(id=4)]
    merged = rrf_merge([a, b], top_n=4)
    ids = [c.id for c in merged]
    # id 3 (high in both) wins; id 2 (mid in both) second; then 1, then 4
    assert ids == [3, 2, 1, 4]
    assert set(ids) == {1, 2, 3, 4}


def test_rrf_merge_respects_top_n():
    a = [NS(id=i) for i in range(10)]
    assert len(rrf_merge([a], top_n=3)) == 3
