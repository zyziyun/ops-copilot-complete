def rrf_merge(ranked_lists: list[list], k: int = 60, top_n: int = 10) -> list:
    scores: dict[int, float] = {}
    by_id: dict[int, object] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank + 1)
            by_id[chunk.id] = chunk
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [by_id[cid] for cid in ordered[:top_n]]
