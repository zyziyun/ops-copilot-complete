import json

from app.clients import aclient
from app.config import settings
from app.models import Chunk


async def llm_rerank(query: str, chunks: list[Chunk], top_n: int = 5) -> list[Chunk]:
    listing = "\n".join(f"[{i}] {c.content[:300]}" for i, c in enumerate(chunks))
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n\nCandidates:\n{listing}\n\n"
                    f"Return ONLY a JSON array of the {top_n} most relevant candidate "
                    "indices, best first. Example: [3,0,7,1,9]"
                ),
            }
        ],
    )
    raw = resp.choices[0].message.content.strip().strip("`")
    try:
        idxs = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        # model wrapped output in prose: fall back to pre-rerank order
        return chunks[:top_n]
    return [chunks[i] for i in idxs if isinstance(i, int) and i < len(chunks)][:top_n]
