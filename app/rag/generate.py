from app.clients import aclient
from app.config import settings
from app.models import Chunk

SYSTEM = (
    "Answer using ONLY the numbered sources. Cite inline like [1], [2]. "
    "If the answer is not in the sources, say you do not know."
)


async def generate(question: str, chunks: list[Chunk]) -> dict:
    context = "\n\n".join(f"[{i + 1}] {c.content}" for i, c in enumerate(chunks))
    resp = await aclient.chat.completions.create(
        model=settings.chat_model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Sources:\n{context}\n\nQuestion: {question}",
            },
        ],
    )
    return {
        "answer": resp.choices[0].message.content,
        "sources": [
            {
                "n": i + 1,
                "source": c.source,
                "source_system": c.source_system,
                "chunk": c.chunk_index,
            }
            for i, c in enumerate(chunks)
        ],
    }
