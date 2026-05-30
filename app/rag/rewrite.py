"""Query-side enhancements that improve recall before retrieval.

- ``rewrite_query``  — expand one question into several diverse search queries
  (synonyms, exact error tokens, broader/narrower) and retrieve for all of them.
- ``hyde_embedding`` — HyDE: generate a *hypothetical answer* and embed that
  instead of the question, since an answer's embedding usually sits closer to the
  real document chunks than the question's does.
"""
import json

from app.clients import aclient, embed_texts
from app.config import settings


async def rewrite_query(query: str, n: int = 3) -> list[str]:
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0.3,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Rewrite this ops question into {n} diverse search queries "
                    "(synonyms, exact error tokens, broader and narrower forms). "
                    "Return ONLY a JSON array of strings.\n\n"
                    f"Question: {query}"
                ),
            }
        ],
    )
    raw = resp.choices[0].message.content.strip().strip("`")
    try:
        variants = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return [query]
    return [query] + [v for v in variants if isinstance(v, str)][:n]


async def hyde_embedding(query: str) -> list[float]:
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a short, factual paragraph (3-4 sentences) that would "
                    "answer this ops question, as if quoted from a runbook:\n\n"
                    f"{query}"
                ),
            }
        ],
    )
    return (await embed_texts([resp.choices[0].message.content]))[0]
