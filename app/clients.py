from openai import AsyncOpenAI

from app.config import settings


def _build_embed_client() -> AsyncOpenAI:
    if settings.ollama_base_url:
        return AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
            timeout=120.0,
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


aclient = _build_embed_client()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    resp = await aclient.embeddings.create(model=settings.embed_model, input=texts)
    return [row.embedding for row in resp.data]
